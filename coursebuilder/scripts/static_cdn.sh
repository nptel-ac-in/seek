
#import config variables
. "$(dirname "$0")/common.sh"

# upload the files inside $SOURCE_DIR/lib/_static to gcloud
GCLOUD_BUCKET="static-prod-v11"

# RSYNC standard libraries
gsutil -m rsync -r $SOURCE_DIR/lib/_static/codemirror-4.5.0 gs://$GCLOUD_BUCKET/static/codemirror
gsutil -m rsync -r $SOURCE_DIR/lib/_static/crossfilter-1.3.7 gs://$GCLOUD_BUCKET/static/crossfilter-1.3.7
gsutil -m rsync -r $SOURCE_DIR/lib/_static/d3-3.4.3 gs://$GCLOUD_BUCKET/static/d3-3.4.3
gsutil -m rsync -r $SOURCE_DIR/lib/_static/dagre-0.7.4 gs://$GCLOUD_BUCKET/static/dagre-0.7.4
gsutil -m rsync -r $SOURCE_DIR/lib/_static/dagre-d3-0.4.17p gs://$GCLOUD_BUCKET/static/dagre-d3-0.4.17p
gsutil -m rsync -r $SOURCE_DIR/lib/_static/dc.js-1.6.0 gs://$GCLOUD_BUCKET/static/dc.js-1.6.0
gsutil -m rsync -r $SOURCE_DIR/lib/_static/dependo-0.1.4 gs://$GCLOUD_BUCKET/static/dependo-0.1.4
gsutil -m rsync -r $SOURCE_DIR/lib/_static/html-imports gs://$GCLOUD_BUCKET/static/html-imports
gsutil -m rsync -r $SOURCE_DIR/lib/_static/inputex-3.1.0 gs://$GCLOUD_BUCKET/static/inputex-3.1.0
gsutil -m rsync -r $SOURCE_DIR/lib/_static/jquery-2.2.4 gs://$GCLOUD_BUCKET/static/jquery
gsutil -m rsync -r $SOURCE_DIR/lib/_static/jqueryui-1.11.4 gs://$GCLOUD_BUCKET/static/jqueryui
gsutil -m rsync -r $SOURCE_DIR/lib/_static/material-design-iconic-font-1.1.1 gs://$GCLOUD_BUCKET/static/material-design-icons
gsutil -m rsync -r $SOURCE_DIR/lib/_static/polymer-1.2.0 gs://$GCLOUD_BUCKET/static/polymer-1.2.0
gsutil -m rsync -r $SOURCE_DIR/lib/_static/polymer-guide-1.2.0 gs://$GCLOUD_BUCKET/modules/guide/resources/polymer
gsutil -m rsync -r $SOURCE_DIR/lib/_static/underscore-1.4.3 gs://$GCLOUD_BUCKET/static/underscore-1.4.3
gsutil -m rsync -r $SOURCE_DIR/lib/_static/yui_2in3-2.9.0 gs://$GCLOUD_BUCKET/static/2in3
gsutil -m rsync -r $SOURCE_DIR/lib/_static/yui_3.6.0 gs://$GCLOUD_BUCKET/static/yui_3.6.0

# RSYNC the assets
gsutil -m rsync -r $SOURCE_DIR/assets   gs://$GCLOUD_BUCKET/explorer/assets/
gsutil -m rsync -r $SOURCE_DIR/assets   gs://$GCLOUD_BUCKET/assets/

# RSYNC some of the heavily used module assets
gsutil -m rsync -r $SOURCE_DIR/modules/nptel/assets gs://$GCLOUD_BUCKET/modules/nptel/assets/
gsutil -m rsync -r $SOURCE_DIR/modules/oeditor/_static gs://$GCLOUD_BUCKET/modules/oeditor/_static/

# RSYNC MathJax by extracting first
# This is special in the way its setup in the module and hence a little different here

unzip $SOURCE_DIR/lib/mathjax-2.3.0.zip -d $SOURCE_DIR/lib/_static/MathJax
unzip $SOURCE_DIR/lib/mathjax-fonts-2.3.0.zip -d $SOURCE_DIR/lib/_static/MathJax/
gsutil -m rsync -r $SOURCE_DIR/lib/_static/MathJax gs://$GCLOUD_BUCKET/modules/math/MathJax
rm -R $SOURCE_DIR/lib/_static/MathJax

# make them public redable
gsutil defacl set public-read gs://$GCLOUD_BUCKET
gsutil defacl ch -u AllUsers:R gs://$GCLOUD_BUCKET

# Enable get cors - one time 
# gsutil cors set static-cdn-cors-settings.json gs://$GCLOUD_BUCKET