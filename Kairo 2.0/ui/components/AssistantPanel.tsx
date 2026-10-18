"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import IntegrationsPanel from "./IntegrationsPanel";



type Review = { token: string; task: string; tool: string; details: Record<string, unknown> };

type Entry = { id: number; kind: string; payload: Record<string, unknown> };

type Memory = { id: string; text?: string; proposition?: string };



export default function AssistantPanel({ onState }: { onState: (state: string, level: number) => void }) {

  const [clock, setClock] = useState("");
  const [answer, setAnswer] = useState("");
  const [showAnswer, setShowAnswer] = useState(false);
  const [request, setRequest] = useState("");
  const [connected, setConnected] = useState(false);

  const [state, setState] = useState("offline");

  const [status, setStatus] = useState("Connecting to KAIRO…");

  const [error, setError] = useState("");

  const [presence, setPresence] = useState("disabled");

  const [claps, setClaps] = useState(false);

  const [threshold, setThreshold] = useState(.35);

  const [devices, setDevices] = useState("");

  const [outputs, setOutputs] = useState<{id:number; name:string; hostapi:string; output:number}[]>([]);

  const [notice, setNotice] = useState("");

  const [pairing, setPairing] = useState("");

  const [scopes, setScopes] = useState<string[]>([]);

  const [mobile, setMobile] = useState(false);

  const [mirroring, setMirroring] = useState(false);

  const [addresses, setAddresses] = useState<string[]>([]);

  const [address, setAddress] = useState("");

  const [phoneUrl, setPhoneUrl] = useState("");

  const [certificate, setCertificate] = useState<{certificate:string;trust_file:string;fingerprint:string}|null>(null);



  const [review, setReview] = useState<Review | null>(null);

  const [memories, setMemories] = useState<Memory[]>([]);

  const [activity, setActivity] = useState<Record<string, unknown>[]>([]);

  const [integrations, setIntegrations] = useState(false);
  const [settings, setSettings] = useState(false);

  const [endpoint, setEndpoint] = useState("");

  const [model, setModel] = useState("");

  const [provider, setProvider] = useState("gemini_live");

  const [voice, setVoice] = useState("Charon");



  const openPanel = useCallback((panel: string) => {
    setSettings(panel === "settings"); setMobile(panel === "mobile");
    setIntegrations(panel === "integrations"); setShowAnswer(panel === "conversation");
    document.querySelector<HTMLDetailsElement>(".scene-menu")?.removeAttribute("open");
  }, []);

  const token = useRef("");

  const cursor = useRef(0);

  const callback = useRef(onState);

  callback.current = onState;



  const command = useCallback(async (data: Record<string, unknown>) => {

    setError("");

    try {

      const response = await fetch("/api/command", { method: "POST", headers: {

        "Content-Type": "application/json", Authorization: `Bearer ${token.current}`,

      }, body: JSON.stringify(data) });

      const result = await response.json();

      if (!response.ok) throw new Error(result.error || "Request failed");

      return result;

    } catch (e) { setError(e instanceof Error ? e.message : "Connection failed"); return null; }

  }, []);



  useEffect(() => {

    const value = new URLSearchParams(location.hash.slice(1)).get("token");

    if (value) { sessionStorage.setItem("kairo-token", value); history.replaceState(null, "", location.pathname); }

    token.current = value || sessionStorage.getItem("kairo-token") || "";

    const tick = () => setClock(new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"}));
    tick();
    const clockTimer = setInterval(tick, 1000);
    const keys = (event: KeyboardEvent) => {
      if (event.key === "Escape") { setSettings(false); setMobile(false); setShowAnswer(false); setIntegrations(false); }
      if (event.ctrlKey && event.key === ",") { event.preventDefault(); openPanel("settings"); }
    };
    window.addEventListener("keydown", keys);
    let disposed = false;

    let timer: ReturnType<typeof setTimeout>;

    const abort = new AbortController();

    async function poll() {

      try {

        const response = await fetch(`/api/events?after=${cursor.current}`, { headers: { Authorization: `Bearer ${token.current}` }, signal: abort.signal });

        const data = await response.json();

        if (!response.ok) throw new Error(data.error);

        if (disposed) return;

        setConnected(true); setState(data.state.state); setStatus(data.state.text); setReview(data.approval);

        if (data.presence) setPresence(data.presence);
        callback.current(data.state.state, Number(data.audio || 0) / 100);

        cursor.current = data.cursor;

        setMirroring(Boolean(data.mirroring));



        for (const entry of data.events as Entry[]) {

          if (entry.kind === "presence") setPresence(String(entry.payload.mode));

          if (entry.kind === "panel" && entry.payload.panel === "settings") openPanel("settings");
          if (entry.kind === "result") { setAnswer(String(entry.payload.answer || "")); }
          if (entry.kind === "notice") setNotice(String(entry.payload.text));

          if (entry.kind === "audio") callback.current(data.state.state, Number(entry.payload.level) / 100);

          if (entry.kind === "snapshot") {

            setMemories([...(entry.payload.memories as Memory[]), ...(entry.payload.knowledge as Memory[])]);

            setActivity(entry.payload.activity as Record<string, unknown>[]);

          }

        }



      } catch (e) {

        if (!disposed) { setConnected(false); setStatus(e instanceof Error ? e.message : "Disconnected"); callback.current("offline", 0); }

      } finally { if (!disposed) timer = setTimeout(poll, 250); }

    }

    void poll();

    void command({ action: "config" }).then(data => { if (data?.brain) { setEndpoint(data.brain.endpoint || ""); setModel(data.brain.model); setProvider(data.brain.provider || "compatible"); setVoice(data.brain.voice || "Charon"); } });

    return () => { disposed = true; abort.abort(); clearTimeout(timer); clearInterval(clockTimer); window.removeEventListener("keydown", keys); };

  }, [command, openPanel]);



  const busy = ["listening", "thinking", "acting", "permission", "speaking"].includes(state);

  return <section className="assistant-panel" aria-label="KAIRO assistant">

    <time className="standby-clock" suppressHydrationWarning>{clock}</time>
    <div className="presence-status" role="status" aria-live="polite">
      <strong>{!connected ? "Disconnected" : state === "permission" ? "Your approval is needed" : state === "speaking" ? "Speaking" : state === "thinking" ? "Thinking" : state === "acting" ? "Working" : presence === "sleeping" ? "Say Hey Kairo" : state === "listening" ? "Listening" : state === "error" ? "Needs attention" : "KAIRO"}</strong>
      <small><span className={"presence-dot " + presence} />{!connected ? status : presence === "sleeping" ? "Local wake listening" : presence === "active" ? "Conversation active" : "Microphone off"}</small>
    </div>
    <details className="scene-menu"><summary aria-label="Open KAIRO menu" title="KAIRO menu">···</summary><div className="menu-actions">
      <button onClick={() => {openPanel("settings");}}>Settings</button>
      <button onClick={() => {openPanel("mobile");void command({action:"companion_addresses"}).then(data=>{if(data){setAddresses(data.addresses);setAddress(data.addresses[0]||"");}});}}>Connect phone</button>
      <button onClick={() => {openPanel("integrations");}}>Tools &amp; plugins</button>
      <button onClick={() => {openPanel("conversation");}}>Conversation &amp; text input</button>
      <button disabled={!connected} onClick={() => void command({action:"stop"})}>Interrupt &amp; mute</button>
    </div></details>
    {showAnswer && <section className="response-panel" aria-label="Conversation"><button onClick={()=>setShowAnswer(false)}>Close</button><strong>KAIRO</strong><p>{answer || "Ask KAIRO by voice or type below."}</p><form onSubmit={event=>{event.preventDefault();if(request.trim())void command({action:"request",text:request}).then(data=>{if(data)setRequest("");});}}><label className="sr-only" htmlFor="request">Message KAIRO</label><textarea id="request" value={request} onChange={e=>setRequest(e.target.value)} maxLength={12000}/><button disabled={!connected || busy || !request.trim()}>Send</button></form></section>}
    {(error || state === "error") && <p role="alert" className="assistant-error">{error || status}</p>}

    {mirroring && <div className="sharing-strip" role="status">Screen sharing <button onClick={() => void command({action:"companion_mirror_stop"})}>Stop sharing</button></div>}

    {integrations && <IntegrationsPanel command={command} onClose={()=>setIntegrations(false)}/>}
    {mobile && <section className="settings" aria-label="Mobile connection">

      <button onClick={()=>setMobile(false)}>Close</button><strong>Connect your phone</strong>

      <p>Use the same Wi-Fi. Prepare the secure connection once, then pair with a code.</p>

      <label>This PC's LAN address<select value={address} onChange={e=>setAddress(e.target.value)}>{addresses.map(a=><option key={a}>{a}</option>)}</select></label>

      {!addresses.length && <p>No private LAN address found. Connect the PC to Wi-Fi or Ethernet.</p>}

      <button disabled={!address} onClick={()=>void command({action:"companion_prepare",address}).then(data=>{if(data){setCertificate(data);setPhoneUrl('https://'+data.address+':'+data.port+'/');}})}>Prepare secure connection</button>

      {certificate && <div><a download="KAIRO-Phone-Trust.cer" href={'data:application/pkix-cert;base64,'+certificate.certificate}>Save phone trust certificate</a><p>Transfer this certificate to your phone and install it as a trusted CA before opening KAIRO. Never share the server private key.</p><details><summary>Certificate location and fingerprint</summary><p>{certificate.trust_file}</p><small>{certificate.fingerprint}</small></details></div>}

      <label>Allow on this phone</label>

      {[["screen","Live screen"],["pointer","Touchpad"],["keyboard","Keyboard"],["media","Media and volume"],["windows","Open apps and windows"]].map(([scope,label])=><label className="check-label" key={scope}><input type="checkbox" checked={scopes.includes(scope)} onChange={e=>setScopes(old=>e.target.checked?[...old,scope]:old.filter(s=>s!==scope))}/>{label}</label>)}

      <button onClick={()=>void command({action:"companion_start"}).then(data=>{if(data)setPhoneUrl(data.address+'/');})}>Start mobile connection</button>

      {phoneUrl && <p>Open on your phone: <strong>{phoneUrl}</strong></p>}

      <button disabled={!scopes.length} onClick={()=>void command({action:"companion_pair",scopes}).then(data=>{if(data){setPairing(data.code);setTimeout(()=>setPairing("Expired — create another code"),120000);}})}>Create pairing code</button>

      {pairing && <p role="status">Pairing code: <strong>{pairing}</strong></p>}

      <small>Code lasts two minutes. Live screen viewing requires approval on this PC and stops after five minutes.</small>

      <button onClick={()=>void command({action:"companion_revoke"}).then(()=>{setPairing("");setPhoneUrl("");})}>Disconnect all devices</button>

    </section>}

    {settings && <section className="settings" aria-label="Settings">
      <button onClick={()=>setSettings(false)}>Close</button><strong>Voice &amp; privacy</strong>
      <button disabled={!connected} onClick={() => void command({ action: presence === "disabled" ? "wake_enable" : "wake_disable", claps, threshold })}>{presence === "disabled" ? "Enable wake listening on this PC" : "Disable all listening"}</button>
      {presence === "active" && <button onClick={()=>void command({action:"sleep"})}>Return to wake-only mode</button>}

      <p>{status}</p>

      {notice && <p>{notice}</p>}

      <p>Wake speech stays on this PC. Once awake, audio streams to the configured live provider until you say “Kairo, go to sleep”. Enabling wake listening is remembered on this PC; disabling it clears that choice.</p>

      <label className="check-label"><input type="checkbox" checked={claps} disabled={presence !== "disabled"} onChange={e => setClaps(e.target.checked)} />Two-clap wake</label>

      {claps && <label>Clap threshold {threshold.toFixed(2)}<input type="range" min="0.15" max="0.95" step="0.05" value={threshold} disabled={presence !== "disabled"} onChange={e => setThreshold(Number(e.target.value))} /><small>Keep quiet for three seconds after enabling to calibrate.</small></label>}



      <label>Provider<select value={provider} onChange={e => setProvider(e.target.value)}><option value="gemini_live">Gemini Live</option><option value="compatible">Compatible API (optional)</option></select></label>

      {provider === "compatible" && <label>Model endpoint<input value={endpoint} onChange={e => setEndpoint(e.target.value)} /></label>}

      <label>Model name<input value={model} onChange={e => setModel(e.target.value)} /></label>

      {provider === "gemini_live" && <label>Voice<select value={voice} onChange={e => setVoice(e.target.value)}>{["Charon", "Puck", "Kore", "Fenrir", "Aoede"].map(name => <option key={name}>{name}</option>)}</select></label>}

      <p>{provider === "gemini_live" ? "Set GEMINI_API_KEY or KAIRO_CREDENTIALS_FILE in the launcher environment. Live audio streams directly to Gemini. Saving settings starts a fresh conversation." : "Set KAIRO_API_KEY in the launch environment for cloud authentication."}</p>

      <button disabled={!connected || busy} onClick={() => void command({ action: "settings", endpoint, model, provider, voice })}>Save provider</button>

      <button disabled={!connected || busy} onClick={() => void command({ action: "mcp" })}>Connect configured tools</button>

      <button onClick={() => void command({ action: "snapshot" })}>Refresh memory & activity</button>

      <button disabled={busy} onClick={() => void command({ action: "audio_devices" }).then(data => { if (data) { setDevices(JSON.stringify(data, null, 2)); setOutputs(data.devices.filter((d: {output:number}) => d.output > 0)); } })}>Show audio devices</button>

      {outputs.length > 0 && <label>Voice output<select defaultValue="" disabled={busy} onChange={e => void command({action:"audio_select", device:e.target.value === "default" ? null : Number(e.target.value)})}><option disabled value="">Choose playback device</option><option value="default">Windows default output</option>{outputs.map(d => <option key={d.id} value={d.id}>{d.name} ({d.hostapi})</option>)}</select></label>}

      <button disabled={busy} onClick={() => void command({ action: "audio_test" })}>Test Windows voice output</button>

      {devices && <details open><summary>Detected audio devices</summary><pre>{devices}</pre></details>}

      {memories.map(memory => <div key={memory.id}>{memory.text || memory.proposition || "Research memory"}<button onClick={() => void command({ action: "forget", id: memory.id })}>Forget</button></div>)}

      <details><summary>Action history</summary><pre>{JSON.stringify(activity, null, 2)}</pre></details>

    </section>}

    {review && <section className="approval" aria-label="Action approval"><h2>Review action: {review.tool}</h2><pre>{JSON.stringify(review.details, null, 2)}</pre><button onClick={() => void command({ action: "approve", token: review.token, task: review.task, allowed: false })}>Deny</button><button onClick={() => void command({ action: "approve", token: review.token, task: review.task, allowed: true })}>Allow this action</button></section>}



  </section>;

}

