from module.ESIM import *
from module.Utils import *
from module.CPUEmbedding import *
import numpy as np

class BiLSTMModel(nn.Module):
    def __init__(self, vocab, config, init_embedding, elmo_shape):
        super(BiLSTMModel, self).__init__()
        self.config = config
        self.elmo_layers = elmo_shape[0]
        self.elmo_dims = elmo_shape[1]
        initvocab_size, initword_dims = init_embedding.shape
        self.word_dims = initword_dims

        weights = torch.randn(self.elmo_layers)
        self.weights = torch.nn.Parameter(weights, requires_grad=True)
        self.mlp_elmo = nn.Linear(self.elmo_dims, self.word_dims)

        if config.word_dims != initword_dims or vocab.vocab_size != initvocab_size:
            print("prev embedding shape size does not match, check config file")
        self.word_embed = nn.Embedding(vocab.vocab_size, self.word_dims, padding_idx=vocab.PAD)
        self.word_embed.weight.data.copy_(torch.from_numpy(init_embedding))

        self.action_embed = nn.Embedding(vocab.action_size, self.word_dims, padding_idx=vocab.PAD)
        embedding_matrix = np.zeros((vocab.action_size, self.word_dims))
        for i in range(vocab.action_size):
            if i == vocab.PAD: continue
            embedding_matrix[i] = np.random.normal(size=(self.word_dims))
            embedding_matrix[i] = embedding_matrix[i] / np.std(embedding_matrix[i])
        self.action_embed.weight.data.copy_(torch.from_numpy(embedding_matrix))

        self.rnn_dropout = RNNDropout(p=config.dropout_mlp)

        self.hidden_size = config.lstm_hiddens

        self.lstm_enc = Seq2SeqEncoder(nn.LSTM,
                                    2*self.word_dims,
                                    self.hidden_size,
                                    bidirectional=True)

        self.atten = SoftmaxAttention()

        self.hidden_dim = 4*2*config.lstm_hiddens

        self.mlp = nn.Sequential(nn.Linear(4*2*self.hidden_size,
                                        self.hidden_size),
                                        nn.ReLU())

        self.lstm_dec = Seq2SeqEncoder(nn.LSTM,
                                    self.hidden_size,
                                    self.hidden_size,
                                    bidirectional=True)

        self.feature_dim = 2*4*config.lstm_hiddens
        self.proj = nn.Sequential(nn.Dropout(p=config.dropout_mlp),
                                nn.Linear(2*4*self.hidden_size,  self.hidden_size),
                                nn.Tanh(),
                                nn.Dropout(p=config.dropout_mlp),
                                nn.Linear(self.hidden_size, vocab.tag_size))

        self.apply(_init_esim_weights)


    def forward(self, tinputs):
        ##unpack inputs
        src_words, src_actions, src_elmos, src_lens, src_masks, \
        tgt_words, tgt_actions, tgt_elmos, tgt_lens, tgt_masks = tinputs

        src_elmos = src_elmos.matmul(self.weights)
        src_elmo_embed_part = self.mlp_elmo(src_elmos)
        src_action_emb = self.action_embed(src_actions)
        src_elmo_embed = src_elmo_embed_part + src_action_emb

        tgt_elmos = tgt_elmos.matmul(self.weights)
        tgt_elmo_embed_part = self.mlp_elmo(tgt_elmos)
        tgt_action_emb = self.action_embed(tgt_actions)
        tgt_elmo_embed = tgt_elmo_embed_part + tgt_action_emb

        src_dyn_embed = self.word_embed(src_words)
        tgt_dyn_embed = self.word_embed(tgt_words)

        src_embed = torch.cat([src_dyn_embed, src_elmo_embed], dim=-1)
        tgt_embed = torch.cat([tgt_dyn_embed, tgt_elmo_embed], dim=-1)

        src_embed = self.rnn_dropout(src_embed)
        tgt_embed = self.rnn_dropout(tgt_embed)

        src_hiddens = self.lstm_enc(src_embed, src_lens)
        tgt_hiddens = self.lstm_enc(tgt_embed, tgt_lens)


        src_hiddens_att, tgt_hiddens_att = self.atten(src_hiddens, src_masks, \
                                                      tgt_hiddens, tgt_masks)

        src_diff_hiddens = src_hiddens - src_hiddens_att
        src_prod_hiddens = src_hiddens * src_hiddens_att
        src_summary_hiddens = torch.cat([src_hiddens, src_hiddens_att, src_diff_hiddens, \
                                         src_prod_hiddens], dim=-1)

        tgt_diff_hiddens = tgt_hiddens - tgt_hiddens_att
        tgt_prod_hiddens = tgt_hiddens * tgt_hiddens_att
        tgt_summary_hiddens = torch.cat([tgt_hiddens, tgt_hiddens_att, tgt_diff_hiddens, \
                                         tgt_prod_hiddens], dim=-1)

        src_hiddens_proj = self.mlp(src_summary_hiddens)
        tgt_hiddens_proj = self.mlp(tgt_summary_hiddens)

        src_hiddens_proj = self.rnn_dropout(src_hiddens_proj)
        tgt_hiddens_proj = self.rnn_dropout(tgt_hiddens_proj)

        src_final_hiddens = self.lstm_dec(src_hiddens_proj, src_lens)
        tgt_final_hiddens = self.lstm_dec(tgt_hiddens_proj, tgt_lens)

        src_hidden_avg = torch.sum(src_final_hiddens * src_masks.unsqueeze(1)
                                                .transpose(2, 1), dim=1)\
            / (torch.sum(src_masks, dim=1, keepdim=True) + 1e-7)
        tgt_hidden_avg = torch.sum(tgt_final_hiddens * tgt_masks.unsqueeze(1)
                                                  .transpose(2, 1), dim=1)\
            / (torch.sum(tgt_masks, dim=1, keepdim=True) + 1e-7)

        src_hidden_max, _ = replace_masked(src_final_hiddens, src_masks, -1e7).max(dim=1)
        tgt_hidden_max, _ = replace_masked(tgt_final_hiddens, tgt_masks, -1e7).max(dim=1)

        hiddens = torch.cat([src_hidden_avg, src_hidden_max, tgt_hidden_avg, tgt_hidden_max], dim=1)

        outputs = self.proj(hiddens)
        return outputs


def _init_esim_weights(module):
    """
    Initialise the weights of the ESIM model.
    """
    if isinstance(module, nn.Linear):
        nn.init.xavier_uniform_(module.weight.data)
        nn.init.constant_(module.bias.data, 0.0)

    elif isinstance(module, nn.LSTM):
        nn.init.xavier_uniform_(module.weight_ih_l0.data)
        nn.init.orthogonal_(module.weight_hh_l0.data)
        nn.init.constant_(module.bias_ih_l0.data, 0.0)
        nn.init.constant_(module.bias_hh_l0.data, 0.0)
        hidden_size = module.bias_hh_l0.data.shape[0] // 4
        module.bias_hh_l0.data[hidden_size:(2*hidden_size)] = 1.0

        if (module.bidirectional):
            nn.init.xavier_uniform_(module.weight_ih_l0_reverse.data)
            nn.init.orthogonal_(module.weight_hh_l0_reverse.data)
            nn.init.constant_(module.bias_ih_l0_reverse.data, 0.0)
            nn.init.constant_(module.bias_hh_l0_reverse.data, 0.0)
            module.bias_hh_l0_reverse.data[hidden_size:(2*hidden_size)] = 1.0