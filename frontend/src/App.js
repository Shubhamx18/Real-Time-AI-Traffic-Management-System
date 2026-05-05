import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import "./styles.css";
import Settings from "./Settings";

const DEFAULT_SETTINGS = {
  detection: { confidence: 0.20, iou: 0.45, imageSize: 416, model: "YOLOv8x", minTrackFrames: 8, maxDisappeared: 15 },
  signal: { baseGreen: 10, maxGreen: 60, yellowTime: 3, allRedTime: 2, cycleTime: 148, autoMode: true, emergencyPreemption: true, pedestrianPhase: false },
  display: { frameRefreshRate: 500, frameQuality: 70, showTrails: true, showBoundingBoxes: true, showConfidence: true, showVehicleCount: true, theme: "dark" },
  alerts: { congestionThreshold: 15, lowTrafficThreshold: 2, emergencyAlert: true, soundAlerts: true },
  system: { logLevel: "info", maxVideoDuration: 1200, autoCleanup: true, dataRetentionDays: 30 }
};

const DIRS = ["north","south","east","west"];
const DIR_COLORS = {north:"#3b82f6",south:"#22c55e",east:"#f59e0b",west:"#ef4444"};

function App() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [, setResult] = useState(null);  // eslint-disable-line no-unused-vars
  const [loading, setLoading] = useState(false);
  const [loadingElapsed, setLoadingElapsed] = useState(0);
  const [liveProgress, setLiveProgress] = useState(null);
  const [livePhase, setLivePhase] = useState("south");
  const [liveTimeLeft, setLiveTimeLeft] = useState(22);
  const [liveCycle, setLiveCycle] = useState(0);
  const [activeNav, setActiveNav] = useState("live");
  const [densityHistory, setDensityHistory] = useState([]);
  const [, setIsSimulating] = useState(false);  // eslint-disable-line no-unused-vars
  const [, setCycleCount] = useState(0);  // eslint-disable-line no-unused-vars
  const [frameRefresh, setFrameRefresh] = useState(0);
  const [hasDetection, setHasDetection] = useState(false);
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [, setSettingsLoaded] = useState(false);  // eslint-disable-line no-unused-vars
  const [toast, setToast] = useState(null);
  const [systemStats, setSystemStats] = useState(null);
  const [analyticsSummary, setAnalyticsSummary] = useState(null);

  const signalOrderRef = useRef(["south","east","north","west"]);
  const greenTimesRef = useRef({north:16,south:22,east:19,west:10});
  const initializedRef = useRef(false);
  const stoppedRef = useRef(false);
  const abortControllerRef = useRef(null);

  // Elapsed timer
  useEffect(() => {
    if (!loading) { setLoadingElapsed(0); return; }
    const t = setInterval(() => setLoadingElapsed(p => p + 1), 1000);
    return () => clearInterval(t);
  }, [loading]);

  // Refresh camera frames only when detection is active
  useEffect(() => {
    if (!hasDetection) return;
    const t = setInterval(() => setFrameRefresh(p => p + 1), 500);
    return () => clearInterval(t);
  }, [hasDetection]);

  // Poll progress
  useEffect(() => {
    if (!loading) { setLiveProgress(null); return; }
    const p = setInterval(async () => {
      try {
        const r = await axios.get("http://localhost:5000/progress");
        if (r.data?.status === "detecting") setLiveProgress(r.data);
      } catch {}
    }, 1500);
    return () => clearInterval(p);
  }, [loading]);

  // Update refs from live data
  useEffect(() => {
    if (!loading || !liveProgress?.directions) return;
    const dd = liveProgress.directions;
    const sorted = [...DIRS].sort((a,b) => (dd[b]?.queue_count||0) - (dd[a]?.queue_count||0));
    signalOrderRef.current = sorted;
    DIRS.forEach(d => { greenTimesRef.current[d] = dd[d]?.green_time || 10; });
    if (!initializedRef.current && sorted[0]) {
      initializedRef.current = true;
      setLivePhase(sorted[0]);
      setLiveTimeLeft(dd[sorted[0]]?.green_time || 15);
    }
    // Update density history
    setDensityHistory(prev => {
      const entry = { time: `${Math.floor(loadingElapsed/60)}:${String(loadingElapsed%60).padStart(2,"0")}` };
      DIRS.forEach(d => { entry[d] = dd[d]?.vehicles_on_road || 0; });
      const next = [...prev, entry];
      return next.length > 20 ? next.slice(-20) : next;
    });
  }, [loading, liveProgress, loadingElapsed]);

  // Countdown timer
  useEffect(() => {
    if (!loading) { initializedRef.current = false; return; }
    const t = setInterval(() => {
      setLiveTimeLeft(prev => {
        if (prev <= 1) {
          setLivePhase(cur => {
            const s = signalOrderRef.current;
            const idx = s.indexOf(cur);
            const next = s[(idx+1)%4];
            if ((idx+1)%4 === 0) setLiveCycle(c => c+1);
            setLiveTimeLeft(greenTimesRef.current[next] || 10);
            return next;
          });
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [loading]);

  // Load settings from backend on mount
  useEffect(() => {
    axios.get("http://localhost:5000/settings").then(r => {
      if (r.data) {
        setSettings(prev => {
          const merged = { ...prev };
          for (const cat in r.data) { if (merged[cat]) merged[cat] = { ...merged[cat], ...r.data[cat] }; }
          return merged;
        });
      }
      setSettingsLoaded(true);
    }).catch(() => setSettingsLoaded(true));
  }, []);

  // Fetch system stats every 10s
  useEffect(() => {
    const fetchStats = () => {
      axios.get("http://localhost:5000/system/stats").then(r => setSystemStats(r.data)).catch(() => {});
      axios.get("http://localhost:5000/analytics/summary").then(r => setAnalyticsSummary(r.data)).catch(() => {});
    };
    fetchStats();
    const t = setInterval(fetchStats, 10000);
    return () => clearInterval(t);
  }, []);

  // Toast auto-dismiss
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  const showToast = (msg, type = "success") => setToast({ msg, type });

  const saveSettings = async (s) => {
    try {
      await axios.post("http://localhost:5000/settings", s);
      showToast("✅ Settings saved successfully");
    } catch { showToast("❌ Failed to save settings", "error"); }
  };

  const updateSetting = (category, key, value) => {
    setSettings(prev => ({ ...prev, [category]: { ...prev[category], [key]: value } }));
  };

  const resetSettings = async () => {
    try {
      await axios.post("http://localhost:5000/settings/reset");
      setSettings(DEFAULT_SETTINGS);
      showToast("🔄 Settings reset to defaults");
    } catch { showToast("❌ Failed to reset", "error"); }
  };

  const clearFrames = async () => {
    try { await axios.post("http://localhost:5000/system/clear-frames"); setHasDetection(false); showToast("🗑️ Frames cleared"); } catch { showToast("❌ Failed", "error"); }
  };

  const clearAnalytics = async () => {
    try { await axios.post("http://localhost:5000/analytics/clear"); showToast("📊 Analytics cleared"); } catch { showToast("❌ Failed", "error"); }
  };

  const stopAnalytics = async () => {
    try {
      stoppedRef.current = true;
      // Abort the pending upload request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      await axios.post("http://localhost:5000/stop");
      setLoading(false);
      setLiveProgress(null);
      setHasDetection(false);
      showToast("⏹️ Analysis stopped successfully");
    } catch { showToast("❌ Failed to stop", "error"); }
  };

  const handleFileChange = e => setSelectedFiles(Array.from(e.target.files));

  const handleSubmit = async e => {
    e.preventDefault();
    if (selectedFiles.length !== 4) { alert("Please upload exactly 4 videos (N, S, E, W)."); return; }
    
    // Reset ALL state for fresh detection
    stoppedRef.current = false;
    setResult(null);
    setLiveProgress(null);
    setDensityHistory([]);
    setLivePhase("south");
    setLiveTimeLeft(22);
    setLiveCycle(0);
    setLoadingElapsed(0);
    setIsSimulating(false);
    setCycleCount(0);
    setFrameRefresh(0);
    initializedRef.current = false;
    signalOrderRef.current = ["south","east","north","west"];
    greenTimesRef.current = {north:16,south:22,east:19,west:10};
    
    // Start loading and auto-switch to Live Control
    setLoading(true);
    setHasDetection(true);
    setActiveNav("live");
    
    const fd = new FormData();
    selectedFiles.forEach(f => fd.append("videos", f));
    
    // Create AbortController for this request
    const controller = new AbortController();
    abortControllerRef.current = controller;
    
    try {
      const res = await axios.post("http://localhost:5000/upload", fd, {
        headers: {"Content-Type":"multipart/form-data"},
        signal: controller.signal
      });
      abortControllerRef.current = null;
      if (res.data?.status === 'stopped') {
        // Process was stopped by user via /stop endpoint
        return;
      }
      setResult(res.data);
      setLoading(false);
    } catch (err) {
      abortControllerRef.current = null;
      if (stoppedRef.current || axios.isCancel(err)) {
        // User intentionally stopped — don't show error
        return;
      }
      alert("Error processing videos. Check if backend is running."); 
      setLoading(false);
      setHasDetection(false);
    }
  };

  // Helper functions
  const getVeh = d => liveProgress?.directions?.[d]?.vehicles_on_road || 0;
  const getGT = d => liveProgress?.directions?.[d]?.green_time || greenTimesRef.current[d] || 10;
  const totalVehicles = DIRS.reduce((s,d) => s + getVeh(d), 0);
  const maxDir = DIRS.reduce((a,b) => getVeh(a) > getVeh(b) ? a : b);
  const maxVeh = Math.max(...DIRS.map(d => getVeh(d)), 1);

  const getCycleTime = () => DIRS.reduce((s,d) => s + getGT(d), 0);

  const navItems = [{id:"live",label:"Live Control",badge:"LIVE",badgeClass:"live"},{id:"upload",label:"Upload Footage"},{id:"analytics",label:"Analytics"},{id:"settings",label:"Settings"}];
  const navIcons = {live:"📡",upload:"📤",analytics:"📊",settings:"⚙️"};

  return (
    <div className="App">
      <aside className="sidebar">
        <div className="sidebar-logo"><div className="logo-icon">🚦</div><h2>Adaptive Traffic<br/>Signals</h2></div>
        <nav className="sidebar-nav">{navItems.map(item => (
          <button key={item.id} className={`nav-item ${activeNav===item.id?"active":""}`} onClick={() => setActiveNav(item.id)}>
            <span>{navIcons[item.id]}</span><span className="nav-text">{item.label}</span>
            {item.badge && <span className={`nav-badge ${item.badgeClass||""}`}>{item.badge}</span>}
          </button>
        ))}</nav>
        <div className="sidebar-user"><div className="user-avatar">A</div><div className="user-info"><div className="name">Admin</div><div className="role">● System Active</div></div></div>
      </aside>
      <div className="main-content">
        <div className="top-bar">
          <div className="top-bar-left"><h1>{activeNav==="analytics"?"Traffic Analytics":activeNav==="upload"?"Upload Footage":activeNav==="settings"?"System Settings":"Live Traffic Control"}</h1>{activeNav!=="settings"&&<>{hasDetection?<><div className="live-badge"><div className="live-dot"></div> Live</div><span className="fps-badge">{liveProgress?.fps ? `${liveProgress.fps} FPS` : "— FPS"}</span></>:<span style={{fontSize:11,color:"#475569",fontStyle:"italic"}}>Idle — awaiting footage</span>}</>}</div>
          <div className="system-active-btn"><div className="dot"></div> System Active</div>
        </div>

        {/* === LIVE CONTROL PAGE === */}
        {activeNav === "live" && (
        <div className="dashboard-grid">
          <div className="card" style={{display:"flex",flexDirection:"column"}}>
            <div className="card-header"><h3>🔴 Live Intersection Feeds</h3></div>
            <div className="card-body" style={{flex:1,padding:8}}>
              <div className="feeds-grid">{DIRS.map(d => (
                <div key={d} className="feed-cell">
                  <div className="feed-placeholder"></div>
                  {hasDetection ? (
                    <>
                      <img 
                        src={`http://localhost:5000/frame/${d}?t=${frameRefresh}&_=${Date.now()}`} 
                        alt="" 
                        style={{width:"100%",height:"100%",objectFit:"contain",position:"absolute",inset:0,zIndex:1,background:"#0a0e14",opacity:0,transition:"opacity 0.15s"}} 
                        onError={e=>{e.target.style.opacity="0"}} 
                        onLoad={e=>{e.target.style.opacity="1"}}
                      />
                      {loading && !liveProgress && (
                        <div style={{position:"absolute",inset:0,zIndex:2,display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",background:"rgba(10,14,20,.92)",gap:10}}>
                          <div className="spinner" style={{width:28,height:28,border:"3px solid rgba(59,130,246,.2)",borderTop:"3px solid #3b82f6",borderRadius:"50%",animation:"spin 1s linear infinite"}}></div>
                          <span style={{fontSize:11,color:"#64748b",fontWeight:500,textTransform:"uppercase",letterSpacing:1}}>{d}</span>
                          <span style={{fontSize:10,color:"#475569"}}>Initializing AI Engine...</span>
                        </div>
                      )}
                    </>
                  ) : (
                    <div style={{position:"absolute",inset:0,zIndex:1,display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",background:"rgba(10,14,20,.95)",gap:8}}>
                      <div style={{width:40,height:40,borderRadius:"50%",border:"2px solid rgba(100,116,139,.3)",display:"flex",alignItems:"center",justifyContent:"center"}}>
                        <span style={{fontSize:18,opacity:.4}}>📷</span>
                      </div>
                      <span style={{fontSize:11,color:"#475569",fontWeight:500,textTransform:"uppercase",letterSpacing:1}}>{d}</span>
                      <span style={{fontSize:10,color:"#334155"}}>No feed — upload footage to start</span>
                    </div>
                  )}
                  {hasDetection && <span className="feed-live"><span className="live-dot" style={{width:4,height:4}}></span> LIVE</span>}
                </div>
              ))}</div>
            </div>
          </div>
          <div style={{display:"flex",flexDirection:"column",gap:8,overflow:"auto"}}>
            {!hasDetection ? (
              /* Idle state when no detection is running */
              <div className="card" style={{flex:1,display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",gap:16,padding:30}}>
                <div style={{width:64,height:64,borderRadius:"50%",background:"rgba(30,41,59,.5)",border:"2px solid rgba(100,116,139,.2)",display:"flex",alignItems:"center",justifyContent:"center"}}>
                  <span style={{fontSize:28,opacity:.4}}>🚦</span>
                </div>
                <div style={{textAlign:"center"}}>
                  <div style={{fontSize:14,fontWeight:700,color:"#475569",marginBottom:4}}>System Idle</div>
                  <div style={{fontSize:11,color:"#334155",lineHeight:1.5}}>No active detection session.<br/>Go to <span style={{color:"#3b82f6",cursor:"pointer"}} onClick={()=>setActiveNav("upload")}>Upload Footage</span> to start analysis.</div>
                </div>
                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,width:"100%",marginTop:8}}>
                  {DIRS.map(d=>(
                    <div key={d} style={{background:"rgba(15,23,42,.5)",borderRadius:6,padding:"8px 10px",textAlign:"center",border:"1px solid rgba(30,41,59,.3)"}}>
                      <div style={{fontSize:8,color:"#475569",textTransform:"uppercase",letterSpacing:1,marginBottom:2}}>{d}</div>
                      <div style={{fontSize:16,fontWeight:800,color:"#1e293b"}}>—</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
            <>
            {/* Active Signal Header */}
            <div className="card" style={{overflow:"visible"}}>
              <div style={{background:`linear-gradient(135deg, ${DIR_COLORS[livePhase]}15, ${DIR_COLORS[livePhase]}05)`,borderBottom:`1px solid ${DIR_COLORS[livePhase]}30`,padding:"10px 14px",display:"flex",alignItems:"center",justifyContent:"space-between"}}>
                <div style={{display:"flex",alignItems:"center",gap:8}}>
                  <div style={{width:10,height:10,borderRadius:"50%",background:"#22c55e",boxShadow:"0 0 10px #22c55e",animation:"pulse 1.5s infinite"}}></div>
                  <span style={{fontSize:11,fontWeight:700,color:"#e2e8f0",textTransform:"uppercase",letterSpacing:1}}>GREEN SIGNAL</span>
                </div>
                <span style={{fontSize:10,color:"#64748b"}}>CYCLE #{liveCycle+1}</span>
              </div>
              <div style={{padding:"12px 14px"}}>
                {/* Big Countdown + Direction */}
                <div style={{display:"flex",alignItems:"center",gap:14}}>
                  <div style={{position:"relative",width:64,height:64,flexShrink:0}}>
                    <svg viewBox="0 0 64 64" style={{width:64,height:64,transform:"rotate(-90deg)"}}>
                      <circle cx="32" cy="32" r="28" fill="none" stroke="#1e293b" strokeWidth="4"/>
                      <circle cx="32" cy="32" r="28" fill="none" stroke={DIR_COLORS[livePhase]} strokeWidth="4" strokeDasharray={`${2*Math.PI*28}`} strokeDashoffset={`${2*Math.PI*28*(1-liveTimeLeft/getGT(livePhase))}`} strokeLinecap="round" style={{transition:"stroke-dashoffset .5s"}}/>
                    </svg>
                    <div style={{position:"absolute",inset:0,display:"flex",alignItems:"center",justifyContent:"center",flexDirection:"column"}}><span style={{fontSize:20,fontWeight:900,color:"#fff",lineHeight:1}}>{liveTimeLeft}</span><span style={{fontSize:7,color:"#64748b"}}>SEC</span></div>
                  </div>
                  <div style={{flex:1}}>
                    <div style={{fontSize:9,color:"#64748b",textTransform:"uppercase",letterSpacing:1}}>Active Direction</div>
                    <div style={{fontSize:26,fontWeight:900,color:DIR_COLORS[livePhase],lineHeight:1.1}}>{livePhase.toUpperCase()}</div>
                    <div style={{fontSize:10,color:"#94a3b8",marginTop:2}}>{getVeh(livePhase)} vehicles • {getGT(livePhase)}s green</div>
                  </div>
                </div>

                {/* Traffic Light Visual */}
                <div style={{display:"flex",justifyContent:"center",gap:6,margin:"12px 0",padding:"8px 0",background:"rgba(15,23,42,.5)",borderRadius:8,border:"1px solid #1e293b"}}>
                  {signalOrderRef.current.map((d) => {
                    const isGreen = livePhase===d;
                    return (
                      <div key={d} style={{display:"flex",flexDirection:"column",alignItems:"center",gap:4,flex:1}}>
                        <div style={{fontSize:8,fontWeight:700,color:isGreen?"#e2e8f0":"#475569",textTransform:"uppercase"}}>{d.slice(0,1)}</div>
                        <div style={{width:28,background:"#0d1117",borderRadius:14,padding:"3px",display:"flex",flexDirection:"column",gap:2,alignItems:"center",border:"1px solid #1e293b"}}>
                          <div style={{width:8,height:8,borderRadius:"50%",background:!isGreen?"#ef4444":"#1e293b",boxShadow:!isGreen?"0 0 6px #ef4444":"none",transition:"all .3s"}}></div>
                          <div style={{width:8,height:8,borderRadius:"50%",background:"#1e293b"}}></div>
                          <div style={{width:8,height:8,borderRadius:"50%",background:isGreen?"#22c55e":"#1e293b",boxShadow:isGreen?"0 0 6px #22c55e":"none",transition:"all .3s"}}></div>
                        </div>
                        <div style={{fontSize:9,fontWeight:800,color:isGreen?"#22c55e":"#ef4444"}}>{isGreen?"GO":"STOP"}</div>
                      </div>
                    );
                  })}
                </div>

                {/* Direction Cards */}
                <div style={{display:"flex",flexDirection:"column",gap:4}}>
                  {signalOrderRef.current.map((d,i) => {
                    const isGreen = livePhase===d, veh=getVeh(d), pct = maxVeh>0?veh/maxVeh*100:0;
                    return (
                      <div key={d} style={{display:"flex",alignItems:"center",gap:6,padding:"6px 8px",borderRadius:6,background:isGreen?"rgba(34,197,94,.06)":"transparent",border:isGreen?`1px solid rgba(34,197,94,.2)`:"1px solid transparent"}}>
                        <div style={{width:18,height:18,borderRadius:"50%",background:isGreen?"rgba(34,197,94,.15)":"rgba(239,68,68,.1)",display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0}}>
                          <div style={{width:6,height:6,borderRadius:"50%",background:isGreen?"#22c55e":"#ef4444",boxShadow:isGreen?"0 0 4px #22c55e":"none"}}></div>
                        </div>
                        <span style={{fontSize:10,fontWeight:700,color:"#e2e8f0",width:40,textTransform:"uppercase"}}>{d}</span>
                        <span style={{fontSize:14,fontWeight:900,color:"#fff",width:20,textAlign:"right"}}>{veh}</span>
                        <div style={{flex:1,height:3,background:"#1e293b",borderRadius:2,overflow:"hidden"}}><div style={{height:"100%",width:`${pct}%`,background:DIR_COLORS[d],borderRadius:2,transition:"width .5s"}}></div></div>
                        <span style={{fontSize:8,fontWeight:700,color:isGreen?"#22c55e":"#64748b",width:28,textAlign:"right"}}>{isGreen?`${liveTimeLeft}s`:"WAIT"}</span>
                        {i===0 && <span style={{fontSize:6,background:"#f59e0b",color:"#000",padding:"1px 3px",borderRadius:2,fontWeight:800,flexShrink:0}}>HIGH</span>}
                      </div>
                    );
                  })}
                </div>

                {/* Stats Bar */}
                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:4,marginTop:8}}>
                  <div style={{background:"rgba(30,41,59,.5)",borderRadius:4,padding:"4px 6px",textAlign:"center"}}><div style={{fontSize:7,color:"#475569",textTransform:"uppercase"}}>Total</div><div style={{fontSize:13,fontWeight:800,color:"#fff"}}>{totalVehicles}</div></div>
                  <div style={{background:"rgba(30,41,59,.5)",borderRadius:4,padding:"4px 6px",textAlign:"center"}}><div style={{fontSize:7,color:"#475569",textTransform:"uppercase"}}>AI Conf</div><div style={{fontSize:13,fontWeight:800,color:totalVehicles>0?"#22c55e":"#64748b"}}>{totalVehicles>0?"92%":"—"}</div></div>
                  <div style={{background:"rgba(30,41,59,.5)",borderRadius:4,padding:"4px 6px",textAlign:"center"}}><div style={{fontSize:7,color:"#475569",textTransform:"uppercase"}}>Cycle</div><div style={{fontSize:13,fontWeight:800,color:"#fff"}}>{getCycleTime()}s</div></div>
                </div>
                <div style={{marginTop:6,padding:"5px 8px",background:"rgba(59,130,246,.04)",borderRadius:4,border:"1px solid rgba(59,130,246,.1)",fontSize:9,color:"#64748b",textAlign:"center"}}>🤖 AI adapting signal timing • Priority: {maxDir.toUpperCase()} ({getVeh(maxDir)} veh)</div>
              </div>
            </div>

            {/* Signal Cycle Timeline */}
            <div className="card">
              <div className="card-header"><h3>🚦 Signal Cycle</h3><span style={{fontSize:9,color:"#64748b"}}>Sequence: Density-based</span></div>
              <div style={{padding:"10px 14px"}}>
                <div style={{display:"flex",gap:3,marginBottom:8}}>
                  {signalOrderRef.current.map((d,i) => {
                    const isActive=livePhase===d,gt=getGT(d),pct=isActive?((gt-liveTimeLeft)/gt)*100:0;
                    return (
                      <div key={d} style={{flex:gt,display:"flex",flexDirection:"column",gap:3}}>
                        <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline"}}><span style={{fontSize:9,fontWeight:700,color:isActive?"#e2e8f0":"#475569",textTransform:"uppercase"}}>{d}</span><span style={{fontSize:8,color:isActive?"#e2e8f0":"#475569"}}>{isActive?liveTimeLeft:gt}s</span></div>
                        <div style={{height:6,background:"#1e293b",borderRadius:3,overflow:"hidden",border:isActive?"1px solid "+DIR_COLORS[d]+"40":"none"}}><div style={{height:"100%",width:isActive?`${pct}%`:i<signalOrderRef.current.indexOf(livePhase)?"100%":"0%",background:DIR_COLORS[d],borderRadius:3,transition:"width .5s"}}></div></div>
                      </div>
                    );
                  })}
                </div>
                <div style={{display:"flex",justifyContent:"space-between",fontSize:9,color:"#475569"}}><span>⬤ Current: <span style={{color:"#22c55e",fontWeight:700}}>{livePhase.toUpperCase()}</span></span><span>Next: {signalOrderRef.current[(signalOrderRef.current.indexOf(livePhase)+1)%4].toUpperCase()}</span></div>
              </div>
            </div>
            </>
            )}
          </div>
        </div>)}

        {/* === ANALYTICS PAGE === */}
        {activeNav === "analytics" && (()=>{
          const as = analyticsSummary;
          const today = as?.today || {};
          const totalRuns = today.total_runs || 0;
          const totalVeh = today.total_vehicles || 0;
          const avgPerRun = today.avg_vehicles_per_run || 0;
          const peakVeh = today.peak_vehicles || 0;
          const lp = liveProgress?.directions || {};
          const hasLive = Object.keys(lp).length > 0;
          // AI calculations
          const totalQueue = DIRS.reduce((s,d) => s + (lp[d]?.queue_count||0), 0);
          const totalActive = DIRS.reduce((s,d) => s + (lp[d]?.active||0), 0);
          const totalPassed = DIRS.reduce((s,d) => s + (lp[d]?.passed||0), 0);
          const totalUniqueAll = DIRS.reduce((s,d) => s + (lp[d]?.total_unique||0), 0);
          const avgDensity = hasLive ? (DIRS.reduce((s,d) => s + (lp[d]?.density||0), 0) / 4 * 100).toFixed(1) : 0;
          const efficiencyScore = hasLive ? Math.min(100, Math.max(0, Math.round(100 - (totalQueue / Math.max(totalActive, 1)) * 15))) : 0;
          const congestionIdx = hasLive ? Math.min(10, Math.round(totalQueue / 3)) : 0;
          const congestionLevel = congestionIdx <= 3 ? "Low" : congestionIdx <= 6 ? "Moderate" : "High";
          const congestionColor = congestionIdx <= 3 ? "#22c55e" : congestionIdx <= 6 ? "#f59e0b" : "#ef4444";
          // AI recommendations
          const recommendations = [];
          if (hasLive) {
            const busiestDir = DIRS.reduce((a,b) => (lp[a]?.queue_count||0) > (lp[b]?.queue_count||0) ? a : b);
            const quietestDir = DIRS.reduce((a,b) => (lp[a]?.queue_count||0) < (lp[b]?.queue_count||0) ? a : b);
            if ((lp[busiestDir]?.queue_count||0) > 10) recommendations.push({icon:"🔴",text:`Extend green for ${busiestDir.toUpperCase()} — ${lp[busiestDir]?.queue_count} vehicles queued`,priority:"high"});
            if ((lp[quietestDir]?.queue_count||0) === 0) recommendations.push({icon:"🟡",text:`Reduce green for ${quietestDir.toUpperCase()} — no queue detected`,priority:"medium"});
            if (totalPassed > 20) recommendations.push({icon:"🟢",text:`Good throughput: ${totalPassed} vehicles passed through intersection`,priority:"low"});
            if (avgDensity > 15) recommendations.push({icon:"⚠️",text:`High intersection density (${avgDensity}%) — consider cycle adjustment`,priority:"high"});
            if (efficiencyScore > 80) recommendations.push({icon:"✅",text:`System efficiency at ${efficiencyScore}% — operating optimally`,priority:"low"});
          }
          if (!recommendations.length) recommendations.push({icon:"ℹ️",text:"Start a detection run to receive AI recommendations",priority:"info"});
          return (
        <div style={{padding:16,display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:12,overflow:"auto",flex:1,alignContent:"start"}}>

          {/* Row 1: Traffic Density Chart (full width) */}
          <div className="card" style={{gridColumn:"span 3"}}><div className="card-header"><h3>📈 Traffic Density <span style={{fontWeight:400,fontSize:10,color:"#64748b"}}>{densityHistory.length>0?"(Live Session)":"(No Data)"}</span></h3></div>
            <div className="card-body">
              {densityHistory.length > 0 ? (
              <><ResponsiveContainer width="100%" height={200}>
                <AreaChart data={densityHistory}>
                  <defs>{DIRS.map(d=>(<linearGradient key={d} id={`grad-${d}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={DIR_COLORS[d]} stopOpacity={0.3}/><stop offset="100%" stopColor={DIR_COLORS[d]} stopOpacity={0}/></linearGradient>))}</defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b"/><XAxis dataKey="time" tick={{fill:"#64748b",fontSize:10}} axisLine={{stroke:"#1e293b"}}/><YAxis tick={{fill:"#64748b",fontSize:10}} axisLine={{stroke:"#1e293b"}}/>
                  <Tooltip contentStyle={{background:"#0d1117",border:"1px solid #1e293b",borderRadius:6,fontSize:11}}/>
                  {DIRS.map(d=>(<Area key={d} type="monotone" dataKey={d} stroke={DIR_COLORS[d]} fill={`url(#grad-${d})`} strokeWidth={2}/>))}
                </AreaChart>
              </ResponsiveContainer>
              <div style={{display:"flex",gap:16,justifyContent:"center",marginTop:6}}>{DIRS.map(d=>(<span key={d} style={{display:"flex",alignItems:"center",gap:4,fontSize:11,color:"#94a3b8"}}><span style={{width:10,height:3,borderRadius:1,background:DIR_COLORS[d]}}></span>{d.charAt(0).toUpperCase()+d.slice(1)}</span>))}</div></>
              ) : (
                <div style={{display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",height:200,gap:10}}>
                  <span style={{fontSize:32,opacity:.3}}>📊</span>
                  <span style={{fontSize:12,color:"#475569"}}>No density data yet. Run a detection to see live charts.</span>
                </div>
              )}
            </div>
          </div>

          {/* Row 2: AI Insights | Live Queue Analysis | Direction Comparison */}
          {/* AI Insights & Predictions */}
          <div className="card"><div className="card-header"><h3>🧠 AI Insights</h3><span style={{fontSize:9,padding:"2px 6px",background:hasLive?"rgba(34,197,94,.15)":"rgba(100,116,139,.15)",borderRadius:4,color:hasLive?"#22c55e":"#64748b",fontWeight:600}}>{hasLive?"LIVE":"IDLE"}</span></div>
            <div className="card-body" style={{display:"flex",flexDirection:"column",gap:10}}>
              {/* Efficiency Score Ring */}
              <div style={{display:"flex",alignItems:"center",gap:14}}>
                <div style={{position:"relative",width:56,height:56,flexShrink:0}}>
                  <svg viewBox="0 0 56 56" style={{width:56,height:56,transform:"rotate(-90deg)"}}>
                    <circle cx="28" cy="28" r="24" fill="none" stroke="#1e293b" strokeWidth="5"/>
                    <circle cx="28" cy="28" r="24" fill="none" stroke={efficiencyScore>=70?"#22c55e":efficiencyScore>=40?"#f59e0b":"#ef4444"} strokeWidth="5" strokeDasharray={`${2*Math.PI*24}`} strokeDashoffset={`${2*Math.PI*24*(1-efficiencyScore/100)}`} strokeLinecap="round" style={{transition:"all 1s"}}/>
                  </svg>
                  <div style={{position:"absolute",inset:0,display:"flex",alignItems:"center",justifyContent:"center"}}><span style={{fontSize:14,fontWeight:900,color:"#fff"}}>{hasLive?efficiencyScore:"—"}</span></div>
                </div>
                <div>
                  <div style={{fontSize:10,color:"#64748b",textTransform:"uppercase",letterSpacing:1}}>Efficiency Score</div>
                  <div style={{fontSize:13,fontWeight:700,color:efficiencyScore>=70?"#22c55e":efficiencyScore>=40?"#f59e0b":"#ef4444"}}>{hasLive?(efficiencyScore>=70?"Optimal":efficiencyScore>=40?"Fair":"Poor"):"N/A"}</div>
                </div>
              </div>
              {/* Congestion Index */}
              <div style={{padding:"8px 10px",background:"rgba(15,23,42,.5)",borderRadius:6,border:"1px solid rgba(30,41,59,.3)"}}>
                <div style={{display:"flex",justifyContent:"space-between",marginBottom:4}}><span style={{fontSize:9,color:"#64748b",textTransform:"uppercase"}}>Congestion Index</span><span style={{fontSize:10,fontWeight:700,color:congestionColor}}>{hasLive?`${congestionIdx}/10 ${congestionLevel}`:"—"}</span></div>
                <div style={{height:4,background:"#1e293b",borderRadius:2,overflow:"hidden"}}><div style={{height:"100%",width:`${congestionIdx*10}%`,background:`linear-gradient(90deg,#22c55e,#f59e0b,#ef4444)`,borderRadius:2,transition:"width .5s"}}></div></div>
              </div>
              {/* Avg Density */}
              <div style={{display:"flex",justifyContent:"space-between",padding:"6px 10px",background:"rgba(15,23,42,.5)",borderRadius:6,border:"1px solid rgba(30,41,59,.3)"}}>
                <span style={{fontSize:10,color:"#64748b"}}>Avg Intersection Density</span>
                <span style={{fontSize:11,fontWeight:700,color:"#e2e8f0"}}>{hasLive?`${avgDensity}%`:"—"}</span>
              </div>
              <div style={{display:"flex",justifyContent:"space-between",padding:"6px 10px",background:"rgba(15,23,42,.5)",borderRadius:6,border:"1px solid rgba(30,41,59,.3)"}}>
                <span style={{fontSize:10,color:"#64748b"}}>Unique Vehicles Tracked</span>
                <span style={{fontSize:11,fontWeight:700,color:"#e2e8f0"}}>{hasLive?totalUniqueAll:"—"}</span>
              </div>
            </div>
          </div>

          {/* Live Queue Analysis */}
          <div className="card"><div className="card-header"><h3>🚦 Queue Analysis</h3></div>
            <div className="card-body">
              {hasLive ? (
                <div style={{display:"flex",flexDirection:"column",gap:6}}>
                  {DIRS.map(d => {
                    const q = lp[d]?.queue_count||0, m = lp[d]?.moving||0, p = lp[d]?.passed||0, total = q+m;
                    const qPct = total > 0 ? (q/total*100) : 0;
                    return (
                      <div key={d} style={{padding:"6px 8px",background:"rgba(15,23,42,.5)",borderRadius:6,border:"1px solid rgba(30,41,59,.3)"}}>
                        <div style={{display:"flex",justifyContent:"space-between",marginBottom:3}}>
                          <span style={{fontSize:10,fontWeight:700,color:DIR_COLORS[d],textTransform:"uppercase"}}>{d}</span>
                          <span style={{fontSize:9,color:"#64748b"}}>{p} passed</span>
                        </div>
                        <div style={{display:"flex",gap:2,height:6,borderRadius:3,overflow:"hidden"}}>
                          <div style={{width:`${qPct}%`,background:"#ef4444",borderRadius:3,transition:"width .3s",minWidth:q>0?2:0}}></div>
                          <div style={{flex:1,background:"#22c55e",borderRadius:3,opacity:m>0?1:0.2}}></div>
                        </div>
                        <div style={{display:"flex",justifyContent:"space-between",marginTop:2}}>
                          <span style={{fontSize:8,color:"#ef4444"}}>⏹ Waiting: {q}</span>
                          <span style={{fontSize:8,color:"#22c55e"}}>▶ Moving: {m}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",height:180,gap:8}}>
                  <span style={{fontSize:28,opacity:.3}}>🚦</span>
                  <span style={{fontSize:11,color:"#475569"}}>Run detection to see queue data</span>
                </div>
              )}
            </div>
          </div>

          {/* Direction Comparison Heatmap */}
          <div className="card"><div className="card-header"><h3>📊 Direction Comparison</h3></div>
            <div className="card-body">
              {hasLive ? (
                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:6}}>
                  {DIRS.map(d => {
                    const data = lp[d]||{};
                    const density = ((data.density||0)*100).toFixed(1);
                    const intensityBg = `rgba(${data.density>0.15?'239,68,68':data.density>0.05?'245,158,11':'34,197,94'}, ${Math.min(0.2, (data.density||0)*2)})`;
                    return (
                      <div key={d} style={{padding:"10px",background:intensityBg,borderRadius:8,border:`1px solid ${DIR_COLORS[d]}30`,textAlign:"center"}}>
                        <div style={{fontSize:10,fontWeight:700,color:DIR_COLORS[d],textTransform:"uppercase",marginBottom:4}}>{d}</div>
                        <div style={{fontSize:22,fontWeight:900,color:"#fff",lineHeight:1}}>{data.vehicles_on_road||0}</div>
                        <div style={{fontSize:8,color:"#64748b",marginTop:2}}>vehicles on road</div>
                        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:4,marginTop:6}}>
                          <div style={{fontSize:8,color:"#94a3b8"}}>Queue: <span style={{fontWeight:700,color:"#e2e8f0"}}>{data.queue_count||0}</span></div>
                          <div style={{fontSize:8,color:"#94a3b8"}}>Density: <span style={{fontWeight:700,color:"#e2e8f0"}}>{density}%</span></div>
                          <div style={{fontSize:8,color:"#94a3b8"}}>Green: <span style={{fontWeight:700,color:"#22c55e"}}>{data.green_time||0}s</span></div>
                          <div style={{fontSize:8,color:"#94a3b8"}}>Unique: <span style={{fontWeight:700,color:"#e2e8f0"}}>{data.total_unique||0}</span></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",height:180,gap:8}}>
                  <span style={{fontSize:28,opacity:.3}}>🗺️</span>
                  <span style={{fontSize:11,color:"#475569"}}>No live comparison data</span>
                </div>
              )}
            </div>
          </div>

          {/* Row 3: AI Recommendations | Performance Metrics | Detection History */}
          {/* AI Recommendations */}
          <div className="card"><div className="card-header"><h3>🤖 AI Recommendations</h3></div>
            <div className="card-body">
              <div style={{display:"flex",flexDirection:"column",gap:6}}>
                {recommendations.map((r,i) => (
                  <div key={i} style={{display:"flex",alignItems:"flex-start",gap:8,padding:"8px 10px",background:r.priority==="high"?"rgba(239,68,68,.06)":r.priority==="medium"?"rgba(245,158,11,.06)":"rgba(34,197,94,.06)",borderRadius:6,border:`1px solid ${r.priority==="high"?"rgba(239,68,68,.15)":r.priority==="medium"?"rgba(245,158,11,.15)":"rgba(34,197,94,.15)"}`}}>
                    <span style={{fontSize:14,flexShrink:0,marginTop:1}}>{r.icon}</span>
                    <span style={{fontSize:11,color:"#cbd5e1",lineHeight:1.4}}>{r.text}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Performance Metrics */}
          <div className="card"><div className="card-header"><h3>⚡ Performance</h3></div><div className="card-body"><div className="perf-grid">
            {[
              {icon:"🔄",label:"Detection Runs",value:String(totalRuns),unit:"",change:totalRuns>0?"Active":"—",bg:"rgba(34,197,94,.1)",color:"#22c55e"},
              {icon:"🚗",label:"Total Vehicles",value:String(totalVeh),unit:"",change:totalVeh>0?`Peak: ${peakVeh}`:"—",bg:"rgba(59,130,246,.1)",color:"#3b82f6"},
              {icon:"📈",label:"Avg per Run",value:String(avgPerRun),unit:" veh",change:avgPerRun>0?"Tracked":"—",bg:"rgba(168,85,247,.1)",color:"#a855f7"},
              {icon:"🕐",label:"Peak Hour",value:as?.peak_hour||"N/A",unit:"",change:"",bg:"rgba(245,158,11,.1)",color:"#f59e0b"}
            ].map((p,i)=>(
              <div key={i} className="perf-card"><div className="perf-icon" style={{background:p.bg,color:p.color}}>{p.icon}</div><div><span className="perf-value">{p.value}</span><span className="perf-unit">{p.unit}</span>{p.change&&<span className="perf-change up">{p.change}</span>}</div><div className="perf-label">{p.label}</div></div>
            ))}
          </div></div></div>

          {/* Detection History */}
          <div className="card"><div className="card-header"><h3>📋 History</h3><span style={{fontSize:10,color:"#64748b"}}>{as?.total_runs_all_time||0} runs</span></div><div className="card-body">
            {as?.recent_runs?.length > 0 ? (
              <div style={{display:"flex",flexDirection:"column",gap:5}}>
                {as.recent_runs.slice(-5).reverse().map((run,i) => (
                  <div key={i} style={{display:"flex",alignItems:"center",gap:8,padding:"6px 8px",background:"rgba(15,23,42,.5)",borderRadius:6,border:"1px solid rgba(30,41,59,.3)"}}>
                    <span style={{fontSize:9,color:"#64748b",width:24}}>#{run.id}</span>
                    <div style={{flex:1}}>
                      <div style={{fontSize:10,color:"#e2e8f0",fontWeight:600}}>{run.total_vehicles} vehicles</div>
                      <div style={{fontSize:8,color:"#475569"}}>{run.elapsed_time}s</div>
                    </div>
                    <div style={{display:"flex",gap:3}}>
                      {DIRS.map(d=><span key={d} style={{fontSize:8,color:DIR_COLORS[d],fontWeight:700}}>{d.charAt(0).toUpperCase()}:{typeof run.vehicle_counts==='object'?(run.vehicle_counts[d]||0):'?'}</span>)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",padding:20,gap:6}}>
                <span style={{fontSize:24,opacity:.3}}>📋</span>
                <span style={{fontSize:10,color:"#475569"}}>No detection runs yet</span>
              </div>
            )}
          </div></div>

        </div>);
        })()}

        {/* === UPLOAD FOOTAGE PAGE === */}
        {activeNav === "upload" && (
        <div style={{padding:24,maxWidth:800,margin:"0 auto"}}>
          <div className="card">
            <div className="card-header"><h3>📤 Upload Traffic Footage</h3></div>
            <div className="card-body">
              <p style={{color:"#94a3b8",fontSize:12,marginBottom:16}}>Upload 4 videos (North, South, East, West directions) for AI-powered traffic analysis and adaptive signal optimization.</p>
              <form onSubmit={handleSubmit}>
                <label htmlFor="file-input" style={{display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",minHeight:120,border:"2px dashed #1e293b",borderRadius:10,cursor:"pointer",marginBottom:16,padding:20,background:"rgba(15,23,42,.5)",transition:"border-color .2s"}}>
                  <input type="file" multiple accept="video/*" onChange={handleFileChange} id="file-input" style={{display:"none"}}/>
                  <div style={{fontSize:36,marginBottom:8,opacity:.5}}>📁</div>
                  <p style={{fontSize:12,color:"#64748b",margin:0}}>Drag & drop videos here or <span style={{color:"#3b82f6",textDecoration:"underline"}}>click to browse</span></p>
                  <p style={{fontSize:10,color:"#475569",margin:"4px 0 0"}}>Supports MP4, AVI, MOV files</p>
                </label>
                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,marginBottom:16}}>
                  {["North","South","East","West"].map((dir,i) => (
                    <div key={i} style={{display:"flex",alignItems:"center",gap:8,padding:"10px 12px",background:"rgba(15,23,42,.5)",border:"1px solid #1e293b",borderRadius:8}}>
                      <span style={{width:8,height:8,borderRadius:"50%",background:selectedFiles[i]?"#22c55e":"#334155"}}></span>
                      <span style={{fontSize:12,color:"#e2e8f0",flex:1}}>{selectedFiles[i]?.name || `${dir} video`}</span>
                      <span style={{fontSize:9,color:selectedFiles[i]?"#22c55e":"#64748b",fontWeight:600}}>{selectedFiles[i]?"Ready":"Waiting"}</span>
                    </div>
                  ))}
                </div>
                {selectedFiles.length===4 && <div style={{padding:"8px 12px",background:"rgba(34,197,94,.08)",border:"1px solid rgba(34,197,94,.2)",borderRadius:8,marginBottom:12,fontSize:11,color:"#22c55e",textAlign:"center"}}>✓ All 4 videos selected — ready for analysis</div>}
                <button type="submit" disabled={loading||selectedFiles.length!==4} style={{width:"100%",padding:14,background:loading?"#334155":selectedFiles.length===4?"linear-gradient(135deg,#3b82f6,#2563eb)":"#1e293b",color:loading?"#64748b":"#fff",border:"none",borderRadius:8,fontSize:14,fontWeight:700,cursor:loading||selectedFiles.length!==4?"not-allowed":"pointer",transition:"all .2s"}}>
                  {loading?`⏳ ANALYZING... (${loadingElapsed}s elapsed)`:"🚀 START AI ANALYSIS"}
                </button>
                {loading && <div style={{marginTop:10}}><div style={{height:4,background:"#1e293b",borderRadius:2,overflow:"hidden"}}><div style={{height:"100%",width:`${liveProgress?.progress||0}%`,background:"linear-gradient(90deg,#3b82f6,#22c55e)",borderRadius:2,transition:"width .5s"}}></div></div><div style={{display:"flex",justifyContent:"space-between",marginTop:4,fontSize:10,color:"#64748b"}}><span>Progress: {(liveProgress?.progress||0).toFixed(1)}%</span><span>Frame: {liveProgress?.frame||0}/{liveProgress?.total_frames||0}</span></div></div>}
                {loading && (
                  <button type="button" onClick={stopAnalytics} style={{width:"100%",marginTop:10,padding:12,background:"linear-gradient(135deg,#ef4444,#dc2626)",color:"#fff",border:"none",borderRadius:8,fontSize:13,fontWeight:700,cursor:"pointer",display:"flex",alignItems:"center",justifyContent:"center",gap:8,transition:"all .2s"}}>
                    ⏹️ STOP ANALYSIS
                  </button>
                )}
              </form>
            </div>
          </div>
        </div>)}

        {/* === SETTINGS PAGE === */}
        {activeNav === "settings" && (
          <div style={{flex:1,position:"relative",minHeight:0}}>
            <Settings settings={settings} updateSetting={updateSetting} saveSettings={saveSettings} resetSettings={resetSettings} clearFrames={clearFrames} clearAnalytics={clearAnalytics} systemStats={systemStats} showToast={showToast}/>
          </div>
        )}
        {/* Toast notification */}
        {toast && <div className={`toast ${toast.type}`}>{toast.msg}</div>}
      </div>
    </div>
  );
}
export default App;

