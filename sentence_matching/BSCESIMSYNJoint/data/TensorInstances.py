import torch


class TensorInstances:
    def __init__(self, batch_size, slen, tlen):
        self.src_words = torch.zeros(size=(batch_size, slen), requires_grad=False, dtype=torch.long)
        self.src_extwords = torch.zeros(size=(batch_size, slen), requires_grad=False, dtype=torch.long)
        self.src_lens = torch.zeros(size=(batch_size,), requires_grad=False, dtype=torch.long)
        self.src_masks = torch.zeros(size=(batch_size, slen), requires_grad=False, dtype=torch.float)
        self.tgt_words = torch.zeros(size=(batch_size, tlen), requires_grad=False, dtype=torch.long)
        self.tgt_extwords = torch.zeros(size=(batch_size, tlen), requires_grad=False, dtype=torch.long)
        self.tgt_lens = torch.zeros(size=(batch_size,), requires_grad=False, dtype=torch.long)
        self.tgt_masks = torch.zeros(size=(batch_size, tlen), requires_grad=False, dtype=torch.float)
        self.tags = torch.zeros(size=(batch_size,), requires_grad=False, dtype=torch.long)


        self.src_dep_words = torch.zeros(size=(batch_size, slen+1), requires_grad=False, dtype=torch.long)
        self.src_dep_extwords = torch.zeros(size=(batch_size, slen+1), requires_grad=False, dtype=torch.long)
        self.src_dep_masks = torch.zeros(size=(batch_size, slen+1), requires_grad=False, dtype=torch.float)
        self.tgt_dep_words = torch.zeros(size=(batch_size, tlen+1), requires_grad=False, dtype=torch.long)
        self.tgt_dep_extwords = torch.zeros(size=(batch_size, tlen+1), requires_grad=False, dtype=torch.long)
        self.tgt_dep_masks = torch.zeros(size=(batch_size, tlen+1), requires_grad=False, dtype=torch.float)



    def to_cuda(self, device):
        self.src_words = self.src_words.cuda(device)
        self.src_extwords = self.src_extwords.cuda(device)
        self.src_lens = self.src_lens.cuda(device)
        self.src_masks = self.src_masks.cuda(device)
        self.tgt_words = self.tgt_words.cuda(device)
        self.tgt_extwords = self.tgt_extwords.cuda(device)
        self.tgt_lens = self.tgt_lens.cuda(device)
        self.tgt_masks = self.tgt_masks.cuda(device)
        self.tags = self.tags.cuda(device)

        self.src_dep_words = self.src_dep_words.cuda(device)
        self.src_dep_extwords = self.src_dep_extwords.cuda(device)
        self.src_dep_masks = self.src_dep_masks.cuda(device)
        self.tgt_dep_words = self.tgt_dep_words.cuda(device)
        self.tgt_dep_extwords = self.tgt_dep_extwords.cuda(device)
        self.tgt_dep_masks = self.tgt_dep_masks.cuda(device)

    @property
    def inputs(self):
        return (self.src_words, self.src_extwords, self.src_lens, self.src_masks, \
                self.tgt_words, self.tgt_extwords, self.tgt_lens, self.tgt_masks)

    @property
    def depinputs(self):
        return (self.src_dep_words, self.src_dep_extwords, self.src_dep_masks, \
                self.tgt_dep_words, self.tgt_dep_extwords, self.tgt_dep_masks)

    @property
    def outputs(self):
        return self.tags
