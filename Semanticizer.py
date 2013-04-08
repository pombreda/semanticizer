from processors.core import SettingsProcessor, FilterProcessor
from processors.semanticizer import SemanticizeProcessor
from processors.features import FeaturesProcessor, ArticleFeaturesProcessor, ContextFeaturesProcessor
from processors.external import ArticlesProcessor, StatisticsProcessor
from processors.learning import LearningProcessor
from processors.image import AddImageProcessor
from Errors import InitError
from SemanticizerFlaskServer import Server

import logging
import textcat
import os
import glob
import codecs
import time

class Semanticizer(object):
    
    def __init__(self):
        self.logger = logging.getLogger()
    
    def list_lang(self, lm_dir):
        ngram_model = self._load_ngram_model(lm_dir)
        print sorted(ngram_model.listLangs())
    
    def start_server(self,
                     lm_dir,
                     stopword_dir,
                     langloc,
                     include_features=False,
                     run_own_scikit=False,
                     remote_scikit_url=None,
                     pickle_dir=None,
                     article_url=None,
                     num_threads=1,
                     host='0.0.0.0',
                     port=5000,
                     verbose=False,
                     logformat='[%(asctime)-15s][%(levelname)s][%(module)s][%(pathname)s:%(lineno)d]: %(message)s' ):
        ngram_model = self._load_ngram_model(lm_dir)
        stopwords = self._load_stopwords(stopword_dir)
        uniqlangs, wikipedia_ids = self._load_language(langloc, ngram_model.listLangs(), stopwords)
        pipeline = self._load_pipeline(include_features, run_own_scikit, remote_scikit_url, pickle_dir, article_url, num_threads, wikipedia_ids, uniqlangs)
        server = Server()
        server.set_debug(verbose, logformat)
        server.setup_all_routes(pipeline, stopwords, ngram_model)
        server.start(port, host)
        
    def _load_ngram_model(self, lm_dir):
        self.logger.info("Loading ngram model")
        ngram_model = textcat.NGram(lm_dir)
        return ngram_model
    
    def _load_stopwords(self, stopword_dir):
        self.logger.info("Loading stopwords")
        stopwords = {}
        for fname in glob.glob(os.path.join(stopword_dir, "stopwords.*")):
            langcode = os.path.split(fname)[-1].split(".")[-1]
            stopwords[langcode] = {}
            for line in codecs.open(fname, 'r', 'utf-8'):
                stopwords[langcode][line.strip()] = 0
        return stopwords
            
    def _load_language(self, langloc, available_lang, stopwords):
        uniqlangs = {}
        wikipedia_ids = {}
        for lang, langcode, loc in langloc:
            if not langcode in stopwords:
                raise InitError("No stopwords for \"" + langcode + "\", stopwords are available for " + ", ".join(sorted(stopwords)))
            if not lang in available_lang:
                raise InitError("Language \"" + lang + "\" is not available, available languages are: " + ", ".join(sorted(available_lang)))
            if langcode in uniqlangs:
                continue
            wikipedia_ids[langcode] = loc.split('/')[-2]
            uniqlangs[langcode] = [lang, loc]
        #self.langcodes = uniqlangs.keys()
        return (uniqlangs, wikipedia_ids)
    
    
    def _load_pipeline(self,
                       include_features=False,
                       run_own_scikit=False,
                       remote_scikit_url=None,
                       pickle_dir=None,
                       article_url=None,
                       num_threads=1,
                       wikipedia_ids=None,
                       uniqlangs=None):
        pipeline = []
        semanticize_processor = self._load_semanticize_processor(uniqlangs)
        pipeline.append(("Settings", SettingsProcessor()))
        pipeline.append(("Semanticize", semanticize_processor))
        pipeline.append(("Filter", FilterProcessor()))
        if include_features == True:
            self.logger.info("Loading features...")
            start = time.time()
            pipeline.append(("Features", FeaturesProcessor(semanticize_processor, pickle_dir)))
            pipeline.append(("Articles", ArticlesProcessor(wikipedia_ids, article_url, num_threads, pickle_dir)))
            pipeline.append(("Statistics", StatisticsProcessor(uniqlangs.keys(), num_threads, pickle_dir)))
            pipeline.append(("ArticleFeatures", ArticleFeaturesProcessor()))
            pipeline.append(("ContextFeatures", ContextFeaturesProcessor()))
            self.logger.info("Loading features took %.2f seconds." % (time.time() - start))
            if run_own_scikit == True:
                pipeline.append(("Learning", LearningProcessor()))
            else:
                pipeline.append(("Learning", LearningProcessor(remote_scikit_url)))
        pipeline.append(("AddImage", AddImageProcessor()))
        return pipeline
    
    def _load_semanticize_processor(self, uniqlangs):
        semanticize_processor = SemanticizeProcessor()
        start = time.time()
        self.logger.info("Loading semanticizers for langcode(s) " + ", ".join(uniqlangs.keys()))
        semanticize_processor.load_languages(uniqlangs)
        self.logger.info("Loading semanticizers took %.2f seconds." % (time.time() - start))
        return semanticize_processor