import sys
import clr
import json
import nltk

from flexlibs import FLExInitialize, FLExCleanup
from flexlibs import FLExProject

# Import from SIL.LCModel in FieldWorks.
sys.path.append(r"C:\Users\PC\source\repos\FieldWorks\Downloads")
clr.AddReference("SIL.LCModel")
from SIL.LCModel import (
    IMoStemMsa,
    IMultiUnicode,
    IPunctuationForm,
    IStTxtPara,
    IWfiWordform,
    IWfiAnalysis
)
from SIL.LCModel.DomainServices import SegmentServices
from SIL.LCModel.Core.KernelInterfaces import ITsString


def read_tagged_sents(filename):
    with open(filename, 'r') as openfile:
        return json.load(openfile)


def write_tagged_sents(tagged_sents, filename):
    with open(filename, "w") as outfile:
        json.dump(tagged_sents, outfile)


def get_training_data(project_name):
    FLExInitialize()
    project = FLExProject()
    project.OpenProject(projectName=project_name, writeEnabled=False)
    tagged_sents = list()
    segment_num = None
    for text in list(project.lp.InterlinearTexts):
        sentence = list()
        has_analysis = False
        has_non_approved = False
        ss = SegmentServices.StTextAnnotationNavigator(text)
        for _, analysis in enumerate(ss.GetAnalysisOccurrencesAdvancingInStText()):
            if analysis.Segment.Hvo != segment_num:
                if has_analysis and not has_non_approved:
                    tagged_sents.append(sentence)
                sentence = list()
                has_analysis = False
                has_non_approved = False
                segment_num = analysis.Segment.Hvo
            beg = analysis.GetMyBeginOffsetInPara()
            end = analysis.GetMyEndOffsetInPara()
            surface_form = ITsString(analysis.Paragraph.Contents).Text[beg:end]
            pos = None
            if analysis.Analysis.ClassName == "PunctuationForm":
                pos = "Punc"
            elif analysis.Analysis.ClassName == "WfiWordform":
                pos = "Word"
            elif analysis.Analysis.ClassName == "WfiGloss":
                wfi_analysis = IWfiAnalysis(analysis.Analysis.Analysis)
            elif analysis.Analysis.ClassName == "WfiAnalysis":
                wfi_analysis = IWfiAnalysis(analysis.Analysis)
            else:
                assert False
            if not pos:
                for bundle in wfi_analysis.MorphBundlesOS:
                    if bundle.MsaRA and bundle.MsaRA.ClassName == 'MoStemMsa':
                        msa = IMoStemMsa(bundle.MsaRA)
                        pos = msa.PosFieldName
                if wfi_analysis.HumanApprovedNumber == '0':
                    has_non_approved = True
            if not pos:
                pos = "Unknown"
            if pos != "Punc" and pos != "Word":
                has_analysis = True
            sentence.append((surface_form, pos))
    if sentence and has_analysis and not has_non_approved:
        tagged_sents.append(sentence)
    FLExCleanup()
    return tagged_sents


def get_tags(tagged_sents):
    tags = list()
    for sentence in tagged_sents:
        for tagging in sentence:
            tags.append(tagging[1])
    return tags


def get_words(tagged_sents):
    words = list()
    for sentence in tagged_sents:
        for tagging in sentence:
            words.append(tagging[0])
    return words


def get_tagged_words(tagged_sents):
    tagged_words = list()
    for sentence in tagged_sents:
        for tagging in sentence:
            tagged_words.append(tagging)
    return tagged_words


def compare_taggers(tagged_sents):
    # Convert tagged_sents to use tuples.
    tuple_sents = list()
    for sent in tagged_sents:
        tuple_sents.append(list(tuple(word) for word in sent))
    tagged_sents = tuple_sents
    # Split into training set and testing set.
    size = int(len(tagged_sents) * 0.9)
    train_sents = tagged_sents[:size]
    test_sents = tagged_sents[size:]
    # Test default tagger.
    tags = get_tags(train_sents)
    default_tag = nltk.FreqDist(tags).max()
    default_tagger = nltk.DefaultTagger(default_tag)
    accuracy = default_tagger.accuracy(test_sents)
    print(accuracy, "(default tag:", default_tag + ")")
    # Test lookup tagger.
    fd = nltk.FreqDist(get_words(train_sents))
    cfd = nltk.ConditionalFreqDist(get_tagged_words(train_sents))
    most_freq_words = fd.most_common(100000)
    likely_tags = dict((word, cfd[word].max()) for (word, _) in most_freq_words)
    lookup_tagger = nltk.UnigramTagger(model=likely_tags, backoff=default_tagger)
    accuracy = lookup_tagger.accuracy(test_sents)
    print(accuracy, "(lookup tagger)")
    # Unigram tagger
    unigram_tagger = nltk.UnigramTagger(test_sents, backoff=lookup_tagger)
    accuracy = unigram_tagger.accuracy(test_sents)
    print(accuracy, "(unigram tagger)")
    # Bigram tagger
    bigram_tagger = nltk.BigramTagger(train_sents, backoff=unigram_tagger)
    accuracy = bigram_tagger.accuracy(test_sents)
    print(accuracy, "(bigram tagger)")
    # HMM tagger
    trainer = nltk.tag.hmm.HiddenMarkovModelTrainer()
    hmm_tagger = trainer.train_supervised(train_sents)
    accuracy = hmm_tagger.accuracy(test_sents)
    print(accuracy, "(HMM tagger)")


if __name__ == '__main__':
    project_name = "blx-flex"
    filename = project_name + "_training_data.json"
    if False:
        print("Reading training data from", project_name)
        tagged_sents = get_training_data(project_name)
        print(len(tagged_sents), "sentences")
        write_tagged_sents(tagged_sents, filename)
    tagged_sents = read_tagged_sents(filename)
    if False:
        size = int(len(tagged_sents) * 0.01)
        tagged_sents = tagged_sents[:size]
    print(len(tagged_sents), "sentences loaded")
    compare_taggers(tagged_sents)
