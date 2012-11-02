docsouth-import
===============

This is a tool to import XML transcripts (in a particular subset of the [TEI.2](http://www.tei-c.org/release/doc/tei-p4-doc/html/ref-TEI2.html) specification) from the [DocSouth](http://docsouth.unc.edu/) dataset into the Redis database format used by the [contours/segment annotation tool](https://github.com/contours/segment).

The main script is `docsouth-to-redis.py`. See the comments at the top of that file for usage information. You will likely also need to change `SVM_LEARN` and `SVM_CLASSIFY` in `sbd.py` to set the location of your [SVM-Light](http://svmlight.joachims.org/) executables.

`sbd.py`, `sbd_util.py`, and `word_tokenize.py` are the [Splitta](http://code.google.com/p/splitta/) sentence boundary detection tool by Dan Gillick. The `model_svm` contains the SVM-based sentence boundary model from the same tool.

The `docsouth` directory contains the gzipped XML data from DocSouth, with minor modifications. A handful of the files had issues such as one of the speaker definitions being missing, or some of the speechblock tags missing the speaker ID reference. These errors were unambiguous and were corrected manually.

`docsouth.dump.xz` is the xz-compressed output of a complete run of this import tool. It consists of plain text (UTF-8) Redis database commands.

