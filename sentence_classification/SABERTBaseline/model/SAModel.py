from module.Utils import *
from module.MyLSTM import *
from module.ScaleMix import *
import torch.nn.functional as F


class SAModel(nn.Module):
    def __init__(self, vocab, config, input_dims, bert_layers):
        super(SAModel, self).__init__()
        self.config = config
        self.input_dims = input_dims
        self.input_depth = bert_layers if config.bert_tune == 0 else 1
        self.hidden_dims = 2 * config.lstm_hiddens
        self.projections = nn.ModuleList([NonLinear(self.input_dims, self.hidden_dims, activation=GELU()) \
                                          for i in range(self.input_depth)])

        self.rescale = ScalarMix(mixture_size=self.input_depth)

        self.lstm = MyLSTM(
            input_size=self.hidden_dims,
            hidden_size=config.lstm_hiddens,
            num_layers=config.lstm_layers,
            batch_first=True,
            bidirectional=True,
            dropout_in=config.dropout_lstm_input,
            dropout_out=config.dropout_lstm_hidden,
        )

        self.proj = nn.Linear(2 * config.lstm_hiddens, vocab.tag_size, bias=False)

    def forward(self, inputs, masks):
        proj_hiddens = []
        for idx, input in enumerate(inputs):
            cur_hidden = self.projections[idx](input)
            proj_hiddens.append(cur_hidden)

        word_represents = self.rescale(proj_hiddens)

        if self.training:
            word_represents = drop_uni_input_independent(word_represents, self.config.dropout_emb)

        hiddens, _ = self.lstm(word_represents, masks, None)
        hiddens = hiddens.transpose(1, 0)

        mask_values = (masks.unsqueeze(-1).expand(hiddens.size()) - 1) * float('1e6')
        hiddens = hiddens + mask_values
        hiddens = hiddens.permute(0, 2, 1)

        hidden = F.max_pool1d(hiddens, hiddens.size(2)).squeeze(2)
        outputs = self.proj(hidden)

        return outputs
