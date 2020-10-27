import torch
import torch.nn.functional as F


class SentenceClassifier(object):
    def __init__(self, model, bert, vocab):
        self.model = model
        self.bert = bert
        self.vocab = vocab
        p = next(filter(lambda p: p.requires_grad, model.parameters()))
        self.use_cuda = p.is_cuda
        self.device = p.get_device() if self.use_cuda else None

    def dump_bert(self, bert_indices, bert_segments, bert_pieces, bTrain):
        if self.bert.config.bert_tune == 1 and bTrain:
            bert_outputs = self.bert(bert_indices, bert_segments, bert_pieces)
            return bert_outputs
        else:
            with torch.no_grad():
                bert_outputs = self.bert(bert_indices, bert_segments, bert_pieces)
                return bert_outputs

    def forward(self, inputs, actions, word_indexes, masks):
        bert_indices, bert_segments, bert_pieces = inputs[0], inputs[1], inputs[2]
        if self.use_cuda:
            bert_indices = bert_indices.cuda(self.device)
            bert_segments = bert_segments.cuda(self.device)
            bert_pieces = bert_pieces.cuda(self.device)
            masks = masks.cuda(self.device)
            actions = actions.cuda(self.device)

        bert_outputs = self.dump_bert(bert_indices, bert_segments, bert_pieces, self.model.training)

        refined_bert_outputs = []
        mixed_max_length = actions.size(1)

        for bert_output in bert_outputs:
            batch_size, max_length, bert_dims = bert_outputs[0].size()
            refined_bert_output = bert_output.data.new(batch_size, mixed_max_length, bert_dims).zero_()

            for b in range(batch_size):
                for idx, index in enumerate(word_indexes[b]):
                    refined_bert_output[b, index] = refined_bert_output[b, idx]

            refined_bert_outputs.append(refined_bert_output)

        tag_logits = self.model.forward(refined_bert_outputs, actions, masks)
        # cache
        self.tag_logits = tag_logits

    def compute_loss(self, true_tags):
        if self.use_cuda: true_tags = true_tags.cuda()
        loss = F.cross_entropy(self.tag_logits, true_tags)

        return loss

    def compute_accuracy(self, true_tags):
        b, l = self.tag_logits.size()
        pred_tags = self.tag_logits.detach().max(1)[1].cpu()
        tag_correct = pred_tags.eq(true_tags).cpu().sum()

        return tag_correct, b

    def classifier(self, inputs, actions, word_indexes, masks):
        if inputs is not None:
            self.forward(inputs, actions, word_indexes, masks)
        pred_tags = self.tag_logits.detach().max(1)[1].cpu()
        return pred_tags
