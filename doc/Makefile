doc: 
	docco -l linear Semanticizer.js
	docco -l linear advanced.js
	docco -l linear learning.js

all: doc

publish: all
	rsync -av docs/ zookma:/datastore/applications/semanticize/doc/

watch:
	watch "*.js" 1s "make publish" 
