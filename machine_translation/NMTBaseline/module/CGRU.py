import torch.nn as nn

from module import Init
from module.Attention import BahdanauAttention


class CGRUCell(nn.Module):

    def __init__(self,
                 input_size,
                 hidden_size):

        super(CGRUCell, self).__init__()

        self.hidden_size = hidden_size

        self.gru1 = nn.GRUCell(input_size=input_size, hidden_size=hidden_size)
        self.attn = BahdanauAttention(query_size=hidden_size, key_size=self.context_size)
        self.gru2 = nn.GRUCell(input_size=self.context_size, hidden_size=hidden_size)

        self._reset_parameters()

    def _reset_parameters(self):
        for weight in self.gru1.parameters():
            Init.rnn_init(weight.data)

        for weight in self.gru2.parameters():
            Init.rnn_init(weight.data)

    @property
    def context_size(self):
        return self.hidden_size * 2

    def forward(self,
                input,
                hidden,
                context,
                context_mask=None,
                cache=None):

        hidden1 = self.gru1(input, hidden)
        attn_values, _ = self.attn(query=hidden1, memory=context, cache=cache, mask=context_mask)
        hidden2 = self.gru2(attn_values, hidden1)

        return (hidden2, attn_values), hidden2

    def compute_cache(self, memory):
        return self.attn.compute_cache(memory)
