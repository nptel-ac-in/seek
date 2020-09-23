/**
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

var SHOW_SCORES_LABEL = 'Assign scores to individual choices';
var HIDE_SCORES_LABEL = 'Return to choice picker view';
var HIDE_SCORES_WARNING_LABEL =
    'Return to choice-picker (Note: scores will change)';


/* Whether to show the numeric score or a radio/checkbox. */
var setScores = false;
var setScoresToggleButton;
/* Whether a single or multiple selection of choices is allowed. */
var singleSelection = true;


init();
