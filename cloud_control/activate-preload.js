const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('kacaCloud',{
  status:()=>ipcRenderer.invoke('cloud:status'),
  activate:data=>ipcRenderer.invoke('cloud:activate',data),
  setThumbs:v=>ipcRenderer.invoke('cloud:share-thumbnails',v),
  sync:()=>ipcRenderer.invoke('cloud:sync-now')
});
