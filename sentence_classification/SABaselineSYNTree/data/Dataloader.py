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
                worditems = divides[1].strip().split(' ')
                words, heads, rels = [], [], []
                for worditem in worditems:
                    id1 = worditem.rfind('_')
                    id2 = worditem.rfind('_', 0, id1 - 1)
                    words.append(worditem[:id2])
                    heads.append(int(worditem[id2 + 1:id1]))
                    rels.append(worditem[id1 + 1:])
                tag = divides[0].strip()
                cur_data = Instance(words, heads, rels, tag)
                data.append(cur_data)
    return data

def creatVocab(corpusFile, min_occur_count):
    word_counter = Counter()
    rel_counter = Counter()
    tag_counter = Counter()
    alldatas = read_corpus(corpusFile)
    for inst in alldatas:
        for curword, curhead, currel in zip(inst.forms, inst.heads, inst.rels):
            word_counter[curword] += 1
            rel_counter[currel] += 1
        tag_counter[inst.tag] += 1

    return SAVocab(word_counter, rel_counter, tag_counter, min_occur_count)

def insts_numberize(insts, vocab):
    for inst in insts:
        yield inst2id(inst, vocab)

def inst2id(inst, vocab):
    inputs = []
    for form, rel in zip(inst.forms, inst.rels):
        wordid = vocab.word2id(form)
        extwordid = vocab.extword2id(form)
        relid = vocab.rel2id(rel)
        inputs.append([wordid, extwordid, relid])

    return inputs, vocab.tag2id(inst.tag), inst


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


def batch_data_variable(batch, vocab):
    length = len(batch[0].forms)
    batch_size = len(batch)
    for b in range(1, batch_size):
        if len(batch[b].forms) > length: length = len(batch[b].forms)

    words = torch.zeros([batch_size, length], dtype=torch.int64, requires_grad=False)
    extwords = torch.zeros([batch_size, length], dtype=torch.int64, requires_grad=False)
    rels = torch.zeros([batch_size, length], dtype=torch.int64, requires_grad=False)
    masks = torch.zeros([batch_size, length], dtype=torch.float, requires_grad=False)
    tags = torch.zeros([batch_size], dtype=torch.int64, requires_grad=False)
    lengths = []
    heads = []

    b = 0
    for inputs, tagid, inst in insts_numberize(batch, vocab):
        index = 0
        length = len(inputs)
        lengths.append(length)
        heads.append(inst.heads)
        tags[b] = tagid
        for curword in inputs:
            words[b, index] = curword[0]
            extwords[b, index] = curword[1]
            rels[b, index] = curword[2]
            masks[b, index] = 1
            index += 1
        
        b += 1

    return words, extwords, rels, heads, tags, lengths, masks

def batch_variable_inst(insts, tagids, vocab):
    for inst, tagid in zip(insts, tagids):
        pred_tag = vocab.id2tag(tagid)
        yield Instance(inst.words, inst.heads, inst.rels, pred_tag), pred_tag == inst.tag



