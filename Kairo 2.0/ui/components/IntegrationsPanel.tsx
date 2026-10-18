"use client";
import { useCallback, useEffect, useState } from "react";

type Command = (data: Record<string, unknown>) => Promise<any>;
type Adapter = {name:string;url:string;description:string;status:string;sha256?:string;tested_at?:number};
type Remote = {name:string;description:string;supported:boolean};

export default function IntegrationsPanel({command,onClose}:{command:Command;onClose:()=>void}) {
  const [data,setData]=useState<any>(null);
  const [busy,setBusy]=useState(false);
  const [url,setUrl]=useState("http://127.0.0.1:8000/sse");
  const [transport,setTransport]=useState("sse");
  const [remote,setRemote]=useState<Remote[]>([]);
  const [selected,setSelected]=useState<string[]>([]);
  const refresh=useCallback(async()=>{const result=await command({action:"integrations"});if(result)setData(result);},[command]);
  useEffect(()=>{void refresh();},[refresh]);
  async function run(action:Record<string,unknown>){setBusy(true);try{await command(action);await refresh();}finally{setBusy(false);}}
  return <section className="settings integrations-panel" aria-label="Integrations">
    <button onClick={onClose}>Close</button><strong>Tools &amp; plugins</strong>
    <p>Discover capabilities, connect local tools, and review what KAIRO can use.</p>
    <div className="integration-status" role="status">{data?.connected ? `${data.tools.length} MCP tools connected` : data?.connecting ? "Connecting…" : "No MCP connection"}</div>
    {data?.error && <p role="alert">{data.error}</p>}
    <button disabled={busy||data?.connected} onClick={()=>void run({action:"integration_local"})}>Start local utilities</button>
    <small>Built-in tools read the time and basic system information, count words, and format JSON. No file access or command execution.</small>
    {data?.connected && <><p>{data.tools.join(", ")}</p><button disabled={busy} onClick={()=>void run({action:"integration_disconnect"})}>Disconnect MCP tools</button></>}
    <details><summary>Connect another local MCP server</summary><div className="integration-fields">
      <label>Local server URL<input value={url} onChange={e=>{setUrl(e.target.value);setRemote([]);setSelected([]);}} /></label>
      <label>Connection type<select value={transport} onChange={e=>{setTransport(e.target.value);setRemote([]);setSelected([]);}}><option value="sse">SSE</option><option value="streamable-http">Streamable HTTP</option></select></label>
      <button disabled={busy||data?.connected} onClick={async()=>{setBusy(true);try{const result=await command({action:"integration_discover",url,transport});if(result){setRemote(result.tools);setSelected([]);}}finally{setBusy(false);}}}>Discover tools</button>
      {remote.map(tool=><label className="check-label" key={tool.name}><input type="checkbox" disabled={!tool.supported} checked={selected.includes(tool.name)} onChange={e=>setSelected(old=>e.target.checked?[...old,tool.name]:old.filter(n=>n!==tool.name))}/><span>{tool.name}{!tool.supported&&" — unsupported input schema"}<small className="tool-description">{tool.description}</small></span></label>)}
      {remote.length>0&&<button disabled={busy||!selected.length||data?.connected} onClick={()=>void run({action:"integration_connect",url,transport,tools:selected})}>Connect selected tools</button>}
      <small>Custom server descriptions are untrusted. Each custom tool action requires review. Credentials and remote servers are not accepted here.</small>
    </div></details>
    <h2>Plugin library</h2>
    {data?.plugins?.map((plugin:any)=><article className="plugin-entry" key={plugin.id}><strong>{plugin.name}</strong><p>{plugin.description}</p>{plugin.adapters.length>0&&<button disabled={busy} onClick={()=>void run({action:"plugin_prepare",plugin:plugin.id})}>Prepare adapters</button>}</article>)}
    {data?.catalog?.adapters?.length>0&&<h2>Document adapters</h2>}
    {data?.catalog?.adapters?.map((adapter:Adapter)=><article className="plugin-entry" key={adapter.name}><strong>{adapter.description}</strong><p className="adapter-url">{adapter.url}</p><small>{adapter.status}</small>{adapter.status!=="active"&&<div className="adapter-actions"><button disabled={busy} onClick={()=>void run({action:"adapter_test",name:adapter.name})}>Test retrieval</button><button disabled={busy||adapter.status!=="tested"} onClick={()=>void run({action:"adapter_activate",name:adapter.name,url:adapter.url,sha256:adapter.sha256,tested_at:adapter.tested_at})}>Approve &amp; activate</button></div>}</article>)}
    <details><summary>Available capability catalog ({data?.catalog?.tools?.length||0})</summary>{data?.catalog?.tools?.map((tool:any)=><p key={tool.name}><strong>{tool.name}</strong><br/>{tool.description}<br/><small>{tool.approval_required?"Action review required":"Available within its existing scope"}</small></p>)}</details>
  </section>;
}
