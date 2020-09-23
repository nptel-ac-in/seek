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

var ports=[];var isTempStorageCleared=false;var tempStorageError;self.onconnect=function(event)
{var newPort=(event.ports[0]);if(isTempStorageCleared){notifyTempStorageCleared(newPort);return;}
newPort.onmessage=handleMessage;newPort.onerror=handleError;ports.push(newPort);if(ports.length===1)
clearTempStorage();}
function clearTempStorage()
{function didFail(e)
{tempStorageError="Failed to clear temp storage: "+e.message+" "+e.name;console.error(tempStorageError);didClearTempStorage();}
function didGetFS(fs)
{fs.root.createReader().readEntries(didReadEntries,didFail);}
function didReadEntries(entries)
{var remainingEntries=entries.length;if(!remainingEntries){didClearTempStorage();return;}
function didDeleteEntry()
{if(!--remainingEntries)
didClearTempStorage();}
function failedToDeleteEntry(e)
{tempStorageError="Failed to delete entry: "+e.message+" "+e.name;console.error(tempStorageError);didDeleteEntry();}
for(var i=0;i<entries.length;i++){var entry=entries[i];if(entry.isFile)
entry.remove(didDeleteEntry,failedToDeleteEntry);else
entry.removeRecursively(didDeleteEntry,failedToDeleteEntry);}}
self.webkitRequestFileSystem(self.TEMPORARY,10,didGetFS,didFail);}
function didClearTempStorage()
{isTempStorageCleared=true;for(var i=0;i<ports.length;i++)
notifyTempStorageCleared(ports[i]);ports=null;}
function notifyTempStorageCleared(port)
{port.postMessage({type:"tempStorageCleared",error:tempStorageError});}
function handleMessage(event)
{if(event.data.type==="disconnect")
removePort(event.target);}
function handleError(event)
{console.error("Error: "+event.data);removePort(event.target);}
function removePort(port)
{if(!ports)
return;var index=ports.indexOf(port);ports.splice(index,1);}