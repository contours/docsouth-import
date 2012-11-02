#!/usr/bin/env python2

# Converts a particular XML format of interview transcripts to
# the Redis database format used by contours/segment.
# Requirements:
#  - The lxml parsing library.
#  - SVM-Light installed.
#  - Splitta properly configured to use SVM-Light.
#  - Splitta model_svm/ files in the working directory.
# See: http://code.google.com/p/splitta/
#
# Input is a list of XML files on the command line.
# The interview IDs are generated from the filenames.
# The output is Redis database commands on stdout. Text is UTF-8 encoded.
# Before starting, set "next_sentence_number" below!

# Make sure this is greater than the ID of any existing sentences in the database.
next_sentence_number = 1

annotator_id = 'annotators:docsouth'
dataset_id = 'datasets:docsouth'

# Splitta config
import sbd
sbd_model = sbd.load_sbd_model('model_svm/', use_svm=True)

##################################################################
##################################################################

from lxml import etree
import os.path
import sys
from traceback import print_exc

if len(sys.argv) < 2:
    print >> sys.stderr, 'Usage: {0} xml-file ...'.format(sys.argv[0])
    sys.exit(1)

print 'SADD "datasets" "{0}"'.format(dataset_id)
print 'SADD "annotators" "{0}"'.format(annotator_id)
for filename in sys.argv[1:]:
    print >> sys.stderr, 'Processing file: {0}'.format(filename)
    try:
        doc = etree.parse(filename)
    except etree.XMLSyntaxError as e:
        print >> sys.stderr, 'Error parsing {0}'.format(filename)
        print_exc(file=sys.stderr)

    #interview_id = 'interviews:'+doc.xpath('/TEI.2/text')[0].get('id')
    interview_id = 'interviews:'+os.path.basename(filename).split('.')[0]
    print 'SADD "interviews" "{0}"'.format(interview_id)
    print 'SADD "{0}" "{1}"'.format(dataset_id,interview_id)

    # Add segmentation to indices
    print 'SADD "{0}:{1}:done" "{2}"'.format(annotator_id,dataset_id,interview_id)
    print 'SADD "segmentations" "{0}:{1}:{2}"'.format(annotator_id,dataset_id,interview_id)
    print 'SADD "{0}:segmentations" "{0}:{1}:{2}"'.format(annotator_id,dataset_id,interview_id)
    print 'SADD "{1}:segmentations" "{0}:{1}:{2}"'.format(annotator_id,dataset_id,interview_id)
    print 'SADD "{2}:segmentations" "{0}:{1}:{2}"'.format(annotator_id,dataset_id,interview_id)

    speaker_ids = {}
    for spk in doc.xpath('//text/body/div1/list/item/name'):
        # collapse whitespace in the speaker's name
        speaker_name = ' '.join(spk.text.split())
        speaker_ids[spk.get('id')] = 'speakers:{0}/{1}'.format(interview_id.split(':',1)[1],speaker_name)
        print 'SADD "{0}:speakers" "speakers:{1}/{2}"'.format(interview_id,interview_id.split(':',1)[1],speaker_name)

    next_speechblock_number = 1

    speechblock_id = None
    speaker_id = None
    next_sentence_callback = None

    for e in doc.xpath('//sp | //sp/p | //milestone'):
        if e.tag == 'sp':
            speechblock_id = 'speechblocks:{0}/{1}'.format(interview_id.split(':',1)[1],next_speechblock_number)
            next_speechblock_number += 1
            speaker_id = speaker_ids[e.get('who')]
            print 'RPUSH "{0}:speechblocks" "{1}"'.format(interview_id,speechblock_id)
            print 'RPUSH "{0}:speechblocks" "{1}"'.format(speaker_id,speechblock_id)
        elif e.tag == 'p':
            # milestones do not occur within a <p>
            sentences = sbd.sbd_text(sbd_model,' '.join(e.itertext()),False)
            for sentence_index, sentence_text in enumerate(sentences):
                # Milestone expects to be called at the very next sentence.
                sentence_id = 'sentences:{0}'.format(next_sentence_number)
                next_sentence_number += 1
                print 'RPUSH "{0}:sentences" "{1}"'.format(interview_id,sentence_id)
                print 'RPUSH "{0}:sentences" "{1}"'.format(speechblock_id,sentence_id)
                print 'RPUSH "{0}:sentences" "{1}"'.format(speaker_id,sentence_id)
                # N.B. text encoding is UTF-8
                # Double quotes must be escaped for Redis syntax
                sentence_text = sentence_text.replace('"','\\"').encode('utf-8')
                print 'HMSET "{0}" "text" "{1}" "index" "{2}" "speechblock" "{3}" "speaker" "{4}" "interview" "{5}"'.format(sentence_id, sentence_text, sentence_index, speechblock_id, speaker_id, interview_id)
                if next_sentence_callback is not None:
                    next_sentence_callback(sentence_id)
                    next_sentence_callback = None

        # Milestones may occur between sibling <sp>s, or within an <sp> and sibling to a <p>.
        elif e.tag == 'milestone':
            # Python's silly closure and scope rules...
            def mkCallback(e):
                def callback(s):
                    # Add a segment marker at the start of each unit.
                    print 'SADD "{0}:{1}:{2}" "{3}"'.format(annotator_id,dataset_id,interview_id,s)
                    # Mark excerpt units as excerpts.
                    if e.get('unit') == 'excerpt':
                        print 'SADD "{0}:{1}:{2}:excerpts" "{3}"'.format(annotator_id,dataset_id,interview_id,s)
                return callback

            if e.get('type') == 'start':
                next_sentence_callback = mkCallback(e)

