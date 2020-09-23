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

/**
 * Make a skill display list from a list of skill titles.
 */
function getSkillList(list) {
  var ol = $('<ol class="skill-display-root"></ol>');
  $.each(list, function() {
    var li = $('<li class="skill"></li>').text(this);
    ol.append(li);
  });
  return ol;
}

/**
 * Return the HTML for a tooltip which lists the skills which overflow over the
 * edge of the display table. If no skills overflow, no tooltip is shown.
 */
function getTooltip(skillDisplayRootElt) {
  var overflow = [];

  $(skillDisplayRootElt).find('> div.extras > ol > li.skill').each(function() {
    var offsetRight = this.offsetLeft + this.offsetWidth;
    if (this.offsetParent.offsetWidth < offsetRight) {
      overflow.push($(this).text());
    }
  });

  if (overflow.length > 0) {
    return getSkillList(overflow);
  } else {
    return null;
  }
}

/**
 * Bind a tooltip handler to the course outline which will show any skills which
 * have overflowed.
 */
function bindSkillListOverflowTooltip() {
  $('div.course-outline').tooltip({
    items: 'div.row',
    content: function() {
      return getTooltip(this);
    },
    position: {
      my: "right top",
      at: "right bottom+10"
    },
    tooltipClass: 'skill-list-tooltip'
  });
}

function init() {
  if ($('div.course-outline').length > 0) {
    // Only initialize if the page contains the  course outline
    bindSkillListOverflowTooltip();
  }
}

init();
