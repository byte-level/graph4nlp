from graph4nlp.pytorch.data.dataset import Text2TextDataItem, Text2TextDataset
from graph4nlp.pytorch.modules.graph_construction.dependency_graph_construction import DependencyBasedGraphConstruction
import torch
import os
import json
from stanfordcorenlp import StanfordCoreNLP
from multiprocessing import Pool
import numpy as np
from graph4nlp.pytorch.modules.utils.padding_utils import pad_2d_vals_no_size

from multiprocessing import Process
import multiprocessing
import tqdm
from graph4nlp.pytorch.modules.utils.vocab_utils import VocabModel, Vocab
from graph4nlp.pytorch.modules.utils import constants
from nltk.tokenize import word_tokenize

class CNNDataset(Text2TextDataset):
    def __init__(self,
                 root_dir,
                 topology_builder,
                 topology_subdir,
                 tokenizer=word_tokenize,
                 lower_case=True,
                 pretrained_word_emb_file=None,
                 use_val_for_vocab=False,
                 seed=1234,
                 device='cpu',
                 thread_number=4,
                 port=9000,
                 timeout=15000,
                 graph_type='static',
                 edge_strategy=None,
                 merge_strategy='tailhead',
                 share_vocab=True,
                 word_emb_size=300,
                 dynamic_graph_type=None,
                 dynamic_init_topology_builder=None,
                 dynamic_init_topology_aux_args=None
                 ):
        super(CNNDataset, self).__init__(root_dir=root_dir,
                                         topology_builder=topology_builder,
                                         topology_subdir=topology_subdir,
                                         tokenizer=tokenizer,
                                         lower_case=lower_case,
                                         pretrained_word_emb_file=pretrained_word_emb_file,
                                         use_val_for_vocab=use_val_for_vocab,
                                         seed=seed,
                                         device=device,
                                         thread_number=thread_number,
                                         port=port,
                                         timeout=timeout,
                                         graph_type=graph_type,
                                         edge_strategy=edge_strategy,
                                         merge_strategy=merge_strategy,
                                         share_vocab=share_vocab,
                                         word_emb_size=word_emb_size,
                                         dynamic_graph_type=dynamic_graph_type,
                                         dynamic_init_topology_builder=dynamic_init_topology_builder,
                                         dynamic_init_topology_aux_args=dynamic_init_topology_aux_args)

    @property
    def raw_file_names(self):
        """3 reserved keys: 'train', 'val' (optional), 'test'. Represent the split of dataset."""
        # return {'train': 'train.json', 'val': "val.json", 'test': 'test.json'}
        # return {'train': 'train-0.json', 'val': "val-0.json", 'test': 'test-0.json'}
        # return {'train': 'train_3w.json', 'val': "val.json", 'test': 'test.json'}
        return {'train': 'train_9w.json', 'val': "val.json", 'test': 'test.json'}

    @property
    def processed_file_names(self):
        """At least 3 reserved keys should be fiiled: 'vocab', 'data' and 'split_ids'."""
        return {'vocab': 'vocab.pt', 'data': 'data.pt'}

    def download(self):
        return

    def build_vocab(self):
        data_for_vocab = self.train
        if self.use_val_for_vocab:
            data_for_vocab = data_for_vocab + self.val

        vocab_model = VocabModel.build(saved_vocab_file=self.processed_file_paths['vocab'],
                                       data_set=data_for_vocab,
                                       tokenizer=self.tokenizer,
                                       lower_case=self.lower_case,
                                       max_word_vocab_size=None,
                                       min_word_vocab_freq=3,
                                       pretrained_word_emb_file=self.pretrained_word_emb_file,
                                       word_emb_size=self.word_emb_size,
                                       share_vocab=self.share_vocab)
        self.vocab_model = vocab_model
        return self.vocab_model

    # @staticmethod
    # def process(topology_builder, data_item, port):
    #     processor_args = {
    #         'annotators': 'ssplit,tokenize,depparse',
    #         "tokenize.options":
    #             "splitHyphenated=false,normalizeParentheses=false,normalizeOtherBrackets=false",
    #         "tokenize.whitespace": False,
    #         'ssplit.isOneSentence': False,
    #         'outputFormat': 'json'
    #     }
    #     print('Connecting to stanfordcorenlp server...')
    #     processor = StanfordCoreNLP('http://localhost', port=int(port), timeout=9000)
    #     processor.switch_language("en")
    #     print('CoreNLP server connected.')
    #     pop_idxs = []
    #     cnt = 0
    #     all = len(data_item)
    #     ret = []
    #     # print(id(data_item[0]), data_item[0].input_text)
    #     for idx, item in enumerate(data_item):
    #         if cnt % 1000 == 0:
    #             print("Port {}, processing: {} / {}".format(port, cnt, all))
    #         cnt += 1
    #         try:
    #             graph = topology_builder.topology(raw_text_data=item.input_text,
    #                                               nlp_processor=processor,
    #                                               processor_args=processor_args,
    #                                               merge_strategy="tailhead",
    #                                               edge_strategy=None,
    #                                               verbase=False)
    #             item.graph = graph
    #         except:
    #             pop_idxs.append(idx)
    #             item.graph = None
    #             print('item does not have graph: ' + str(idx))
    #
    #         # ret.append(graph)
    #         ret.append((item, graph))
    #
    #     ret = [x for idx, x in enumerate(ret) if idx not in pop_idxs]
    #     print("Port {}, finish".format(port))
    #     return ret
    #
    # def build_topology(self, data_items):
    #     """
    #     Build graph topology for each item in the dataset. The generated graph is bound to the `graph` attribute of the
    #     DataItem.
    #     """
    #     # print(id(data_items[0]), data_items[0].input_text)
    #
    #     total = len(data_items)
    #     n_pool = 30
    #     pool = Pool(n_pool)
    #     res_l = []
    #     for i in range(n_pool):
    #         start_index = total * i // n_pool
    #         end_index = total * (i + 1) // n_pool
    #         res_l.append(pool.apply_async(self.process, args=(self.topology_builder, data_items[start_index:end_index], 9000)))
    #     pool.close()
    #     pool.join()
    #
    #     # res_l.append(self.process(self.topology_builder, data_items, 9000))
    #
    #     new_data_items = []
    #     for i in range(n_pool):
    #         # res = res_l[i]
    #         res = res_l[i].get()
    #         for data, graph in res:
    #             new_data_items.append(data)
    #
    #     return new_data_items

    # def _process(self):
    #     if any([os.path.exists(processed_path) for processed_path in self.processed_file_paths.values()]):
    #         if 'val_split_ratio' in self.__dict__:
    #             UserWarning(
    #                 "Loading existing processed files on disk. Your `val_split_ratio` might not work since the data have"
    #                 "already been split.")
    #         return
    #
    #     os.makedirs(self.processed_dir, exist_ok=True)
    #
    #     self.read_raw_data()
    #
    #     self.train = self.build_topology(self.train)
    #     self.test = self.build_topology(self.test)
    #     if 'val' in self.__dict__:
    #         self.val = self.build_topology(self.val)
    #
    #     self.build_vocab()
    #
    #     self.vectorization(self.train)
    #     self.vectorization(self.test)
    #     if 'val' in self.__dict__:
    #         self.vectorization(self.val)
    #
    #     data_to_save = {'train': self.train, 'test': self.test}
    #     if 'val' in self.__dict__:
    #         data_to_save['val'] = self.val
    #     torch.save(data_to_save, self.processed_file_paths['data'])

    def parse_file(self, file_path):
        """
        Read and parse the file specified by `file_path`. The file format is specified by each individual task-specific
        base class. Returns all the indices of data items in this file w.r.t. the whole dataset.
        For Text2TextDataset, the format of the input file should contain lines of input, each line representing one
        record of data. The input and output is separated by a tab(\t).
        Examples
        --------
        input: list job use languageid0 job ( ANS ) , language ( ANS , languageid0 )
        DataItem: input_text="list job use languageid0", output_text="job ( ANS ) , language ( ANS , languageid0 )"
        Parameters
        ----------
        file_path: str
            The path of the input file.
        Returns
        -------
        list
            The indices of data items in the file w.r.t. the whole dataset.
        """
        data = []
        with open(file_path, 'r') as f:
            examples = json.load(f)
            for example_dict in examples:
                # input = ' '.join(example_dict['article'][:10]).lower()
                # output = ' '.join([sent[0]+' .' for sent in example_dict['highlight']]).lower()
                # input = ' '.join(' '.join(example_dict['article']).split()).lower()
                # input = input+input+input+input+input
                input = ' '.join(' '.join(example_dict['article']).split()[:500]).lower()
                output = ' '.join(' '.join(['<t> ' + sent[0] + ' . </t>' for sent in example_dict['highlight']]).split()[:99]).lower()
                if input=='' or output=='':
                    continue
                # output = ' '.join(["%s %s %s" % (constants._SOS_TOKEN, sent[0], constants._EOS_TOKEN) for sent in example_dict['highlight']])
                data_item = Text2TextDataItem(input_text=input, output_text=output, tokenizer=self.tokenizer,
                                              share_vocab=self.share_vocab)
                data.append(data_item)
        return data


if __name__ == "__main__":
    dataset = CNNDataset(root_dir="/raid/ghn/graph4nlp/examples/pytorch/summarization/cnn",
                         topology_builder=DependencyBasedGraphConstruction,
                         topology_subdir='DependencyGraph_3w',
                         word_emb_size=128,
                         share_vocab=True)

    # dataset = CNNDataset(root_dir="/raid/ghn/graph4nlp/examples/pytorch/summarization/cnn",
    #                      topology_builder=LinearGraphConstruction,
    #                      topology_subdir='LinearGraph',
    #                      word_emb_size=128,
    #                      share_vocab=True)

    # dataset = CNNSeq2SeqDataset(root_dir="/raid/ghn/graph4nlp/examples/pytorch/summarization/cnn",
    #                             topology_builder=DependencyBasedGraphConstruction,
    #                             topology_subdir='DependencyGraph_seq2seq', share_vocab=True)
    # a  = 0