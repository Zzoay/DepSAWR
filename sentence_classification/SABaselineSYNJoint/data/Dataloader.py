from collections import Counter
from data.Vocab import *
from data.SA import *
import numpy as np
import torch

def read_corpus(file_path):
    data = []
    with open(file_path, 'r') as infile:
        for line in infile:
            divides = line.strip().split('|||')
            section_num = len(divides)
            if section_num == 2:
                words = divides[1].strip().split(' ')
                tag = divides[0].strip()
                cur_data = Instance(words, tag)
                data.append(cur_data)
    return data

def creatVocab(corpusFile, min_occur_count):
    word_counter = Counter()
    tag_counter = Counter()
    alldatas = read_corpus(corpusFile)
    for inst in alldatas:
        for curword in inst.forms:
            word_counter[curword] += 1
        tag_counter[inst.tag] += 1

    return SAVocab(word_counter, tag_counter, min_occur_count)

def insts_numberize(insts, vocab, dep_vocab):
    for inst in insts:
        yield inst2id(inst, vocab, dep_vocab)

def inst2id(inst, vocab, dep_vocab):
    inputs = []
    for curword in inst.forms:
        wordid = vocab.word2id(curword)
        extwordid = vocab.extword2id(curword)
        dep_wordid = dep_vocab.word2id(curword)
        dep_extwordid = dep_vocab.extword2id(curword)
        inputs.append([wordid, extwordid, dep_wordid, dep_extwordid])

    return inputs, vocab.tag2id(inst.tag)


def batch_slice(data, batch_size):
    batch_num = int(np.ceil(len(data) / float(batch_size)))
    for i in range(batch_num):
        cur_batch_size = batch_size if i < batch_num - 1 else len(data) - batch_size * i
        insts = [data[i * batch_size + b] for b in range(cur_batch_size)]

        yield insts


def data_iter(data, batch_size, shuffle=True):
    """
    randomly permute data, then sort by source length, and partition into batches
    ensure that the length of  insts in each batch
    """

    batched_data = []
    if shuffle: np.random.shuffle(data)
    batched_data.extend(list(batch_slice(data, batch_size)))

    if shuffle: np.random.shuffle(batched_data)
    for batch in batched_data:
        yield batch


def batch_data_variable(batch, vocab, dep_vocab):
    length = len(batch[0].forms)
    batch_size = len(batch)
    for b in range(1, batch_size):
        if len(batch[b].forms) > length: length = len(batch[b].forms)

    words = torch.zeros([batch_size, length], dtype=torch.int64, requires_grad=False)
    extwords = torch.zeros([batch_size, length], dtype=torch.int64, requires_grad=False)
    masks = torch.zeros([batch_size, length], dtype=torch.float, requires_grad=False)
    dep_words = torch.zeros([batch_size, length + 1], dtype=torch.int64, requires_grad=False)
    dep_extwords = torch.zeros([batch_size, length + 1], dtype=torch.int64, requires_grad=False)
    dep_masks = torch.zeros([batch_size, length + 1], dtype=torch.float, requires_grad=False)
    tags = torch.zeros([batch_size], dtype=torch.int64, requires_grad=False)

    b = 0
    for inputs, tagid in insts_numberize(batch, vocab, dep_vocab):
        index = 0
        tags[b] = tagid
        dep_words[b, 0], dep_extwords[b, 0], dep_masks[b, 0] = dep_vocab.ROOT, dep_vocab.ROOT, 1
        for curword in inputs:
            words[b, index] = curword[0]
            extwords[b, index] = curword[1]
            masks[b, index] = 1
            dep_words[b, index+1] = curword[2]
            dep_extwords[b, index+1] = curword[3]
            dep_masks[b, index + 1] = 1
            index += 1
        b += 1

    return words, extwords, masks, dep_words, dep_extwords, dep_masks, tags

def batch_variable_inst(insts, tagids, vocab):
    for inst, tagid in zip(insts, tagids):
        pred_tag = vocab.id2tag(tagid)
        yield Instance(inst.words, pred_tag), pred_tag == inst.tag

