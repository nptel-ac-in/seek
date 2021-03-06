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

WebInspector.DevicesView=function()
{WebInspector.VBox.call(this);this.registerRequiredCSS("devicesView.css");this.element.classList.add("devices");this._devicesHelp=this.element.createChild("div");this._devicesHelp.innerHTML=WebInspector.UIString("No devices detected. \
        Please read the <a href=\"https://developers.google.com/chrome-developer\
        -tools/docs/remote-debugging\"> remote debugging documentation</a> to \
        verify your device is enabled for USB debugging.");this.element.createChild("div","devices-info").innerHTML=WebInspector.UIString("Click \"Try here\" button, to open the current page in the selected remote browser.");this._devicesList=this.element.createChild("div");this._devicesList.cellSpacing=0;};WebInspector.DevicesView.MinVersionNewTab=29;var Adb={};Adb.Browser;Adb.Device;WebInspector.DevicesView.Events={DevicesChanged:"DevicesChanged"};WebInspector.DevicesView.prototype={_onDevicesChanged:function(event)
{this._updateDeviceList((event.data));},_updateDeviceList:function(devices)
{function sanitizeForId(id)
{return id.replace(/[.:/\/ ]/g,"-");}
function alreadyDisplayed(element,data)
{var json=JSON.stringify(data);if(element.__cachedJSON===json)
return true;element.__cachedJSON=json;return false;}
function insertChildSortedById(parent,child)
{for(var sibling=parent.firstElementChild;sibling;sibling=sibling.nextElementSibling){if(sibling.id&&sibling.id>child.id){parent.insertBefore(child,sibling);return;}}
parent.appendChild(child);}
function removeObsolete(validIds,section)
{if(validIds.indexOf(section.id)<0)
section.remove();}
if(alreadyDisplayed(this._devicesList,devices))
return;var newDeviceIds=devices.map(function(device){return device.id;});Array.prototype.forEach.call(this._devicesList.querySelectorAll(".device"),removeObsolete.bind(null,newDeviceIds));this._devicesHelp.hidden=!!devices.length;for(var d=0;d<devices.length;d++){var device=devices[d];var deviceSection=this._devicesList.querySelector("#"+sanitizeForId(device.id));if(!deviceSection){deviceSection=this._devicesList.createChild("div","device");deviceSection.id=sanitizeForId(device.id);var deviceHeader=deviceSection.createChild("div","device-header");deviceHeader.createChild("div","device-name");var deviceSerial=deviceHeader.createChild("div","device-serial");deviceSerial.textContent="#"+device.adbSerial.toUpperCase();deviceSection.createChild("div","device-auth");}
if(alreadyDisplayed(deviceSection,device))
continue;deviceSection.querySelector(".device-name").textContent=device.adbModel;deviceSection.querySelector(".device-auth").textContent=device.adbConnected?"":WebInspector.UIString("Pending authentication: please accept debugging session on the device.");var browsers=device.browsers.filter(function(browser){return browser.adbBrowserChromeVersion;});var newBrowserIds=browsers.map(function(browser){return browser.id});Array.prototype.forEach.call(deviceSection.querySelectorAll(".browser"),removeObsolete.bind(null,newBrowserIds));for(var b=0;b<browsers.length;b++){var browser=browsers[b];var incompatibleVersion=browser.hasOwnProperty("compatibleVersion")&&!browser.compatibleVersion;var browserSection=deviceSection.querySelector("#"+sanitizeForId(browser.id));if(!browserSection){browserSection=document.createElementWithClass("div","browser");browserSection.id=sanitizeForId(browser.id);insertChildSortedById(deviceSection,browserSection);var browserName=browserSection.createChild("div","browser-name");browserName.textContent=browser.adbBrowserName;if(browser.adbBrowserVersion)
browserName.textContent+=" ("+browser.adbBrowserVersion+")";if(incompatibleVersion||browser.adbBrowserChromeVersion<WebInspector.DevicesView.MinVersionNewTab){var warningSection=browserSection.createChild("div","warning");warningSection.textContent=incompatibleVersion?WebInspector.UIString("You may need a newer version of desktop Chrome. Please try Chrome %s  or later.",browser.adbBrowserVersion):WebInspector.UIString("You may need a newer version of Chrome on your device. Please try Chrome %s or later.",WebInspector.DevicesView.MinVersionNewTab);}else{var newPageButton=browserSection.createChild("button","settings-tab-text-button");newPageButton.textContent=WebInspector.UIString("Try here");newPageButton.title=WebInspector.UIString("Inspect current page in this browser.");newPageButton.addEventListener("click",InspectorFrontendHost.openUrlOnRemoteDeviceAndInspect.bind(null,browser.id,WebInspector.resourceTreeModel.inspectedPageURL()),true);}}}}},willHide:function()
{WebInspector.inspectorFrontendEventSink.removeEventListener(WebInspector.DevicesView.Events.DevicesChanged,this._onDevicesChanged,this);},wasShown:function()
{WebInspector.inspectorFrontendEventSink.addEventListener(WebInspector.DevicesView.Events.DevicesChanged,this._onDevicesChanged,this);},__proto__:WebInspector.VBox.prototype};