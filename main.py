import sys
import clr
import json
from flexlibs import FLExInitialize, FLExCleanup
from flexlibs import FLExProject

# Import from SIL.LCModel in FieldWorks.
sys.path.append(r"C:\Users\PC\source\repos\FieldWorks\Downloads")
clr.AddReference("SIL.LCModel")
from SIL.LCModel import (
    IMoStemMsa,
    IMultiUnicode,
    IPunctuationForm,
    IWfiWordform,
    IWfiAnalysis
)
from SIL.LCModel.DomainServices import SegmentServices
from SIL.LCModel.Core.KernelInterfaces import ITsString


class FlexCorpus:
    def __init__(self, filename=None):
        self._tagged_sents = list()
        if filename:
            with open(filename, 'r') as openfile:
                json_object = json.load(openfile)
                self._tagged_sents = json_object

    def tagged_sents(self):
        return self._tagged_sents

    def add_tagged_sent(self, sent):
        self._tagged_sents.append(sent)

    def write(self, filename):
        with open(filename, "w") as outfile:
            json.dump(self._tagged_sents, outfile)


def get_training_data(project_name):
    FLExInitialize()
    project = FLExProject()
    project.OpenProject(projectName=project_name, writeEnabled=False)
    corpus = FlexCorpus()
    segment_num = None
    for text in list(project.lp.InterlinearTexts):
        sentence = list()
        has_non_punc = False
        has_non_approved = False
        ss = SegmentServices.StTextAnnotationNavigator(text)
        for _, analysis in enumerate(ss.GetAnalysisOccurrencesAdvancingInStText()):
            if analysis.Segment.Hvo != segment_num:
                if has_non_punc and not has_non_approved:
                    corpus.add_tagged_sent(sentence)
                sentence = list()
                has_non_punc = False
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
            if pos != "Punc":
                has_non_punc = True
            sentence.append((surface_form, pos))
    if sentence and has_non_punc and not has_non_approved:
        corpus.add_tagged_sent(sentence)
    FLExCleanup()
    return corpus


if __name__ == '__main__':
    project_name = "blx-flex"
    filename = project_name + "_training_data.json"
    if True:
        corpus = get_training_data(project_name)
        print(len(corpus.tagged_sents()), "sentences")
        corpus.write(filename)
    corpus = FlexCorpus(filename)
    print(len(corpus.tagged_sents()), "sentences")

