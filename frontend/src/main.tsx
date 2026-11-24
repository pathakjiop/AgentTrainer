import React, { useEffect, useMemo, useState, useRef } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity, AlertCircle, ArrowUpRight, BarChart3, Bot, Check, Copy,
  Database, ExternalLink, FileText, FlaskConical, Globe, Key,
  LayoutDashboard, LogOut, MessageSquare, Plus, RefreshCw, Search, Send,
  Settings, Sparkles, Trash2, Upload, Users, X
} from 'lucide-react';
import './styles.css';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// --- Types ---
type User = { id: string; email: string; full_name: string; role: string };
type Workspace = { id: string; name: string; owner_id: string };
type AgentVersion = {
  id: string;
  version_number: number;
  configuration_snapshot: any;
  change_summary: string;
  is_published: boolean;
  created_at: string;
};
type Agent = {
  id: string;
  name: string;
  description: string;
  category: string;
  model: string;
  provider: string;
  status: string;
  current_version: number;
  system_prompt: string;
  role_description?: string;
  personality?: string;
  restrictions?: string;
  response_format?: string;
  temperature: number;
  max_tokens: number;
  timeout_seconds: number;
  knowledge_base_ids?: string[];
  versions?: AgentVersion[];
};
type KnowledgeBase = {
  id: string;
  name: string;
  description: string;
  documents: { id: string; name: string; file_type: string; file_size: number; chunk_count: number; status: string }[];
};
type Conversation = { id: string; agent_id: string; title: string; updated_at: string };
type Message = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations_json: { source: string; chunk_index: number; relevance: number; snippet: string }[];
  token_count: number;
  latency_ms: number;
  cost_est: number;
  debug_json?: any;
  created_at: string;
};
type DatasetExample = { id: string; question: string; expected_answer: string; category: string };
type Dataset = { id: string; name: string; description: string; examples: DatasetExample[] };
type EvaluationResult = {
  overall_score: number;
  grade: string;
  accuracy: { score: number; feedback: string };
  relevance: { score: number; feedback: string };
  completeness: { score: number; feedback: string };
  instruction_following: { score: number; feedback: string };
  hallucination_risk: { score: number; feedback: string };
  safety: { score: number; feedback: string };
  suggestions: string[];
  feedback: string;
};
type EvaluationRun = {
  id: string;
  agent_id: string;
  agent_version: number;
  overall_score: number;
  grade: string;
  created_at: string;
  summary_json: any;
};
type Deployment = {
  id: string;
  agent_id: string;
  name: string;
  environment: string;
  status: string;
  rate_limit_rpm: number;
  total_requests: number;
  widget_config: { title: string; welcome_message: string; primary_color: string; accent_color: string };
};
type ApiKey = {
  id: string;
  name: string;
  prefix: string;
  is_active: boolean;
  scopes: string;
  created_at: string;
};

// --- Central API Utility ---
async function api(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem('agenttrainer_token');
  const isFormData = options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options.headers as Record<string, string>) || {}),
  };
  const res = await fetch(API + path, { ...options, headers });
  let body: any = {};
  try {
    body = await res.json();
  } catch {}
  if (!res.ok) throw new Error(body.detail || body.message || 'Request failed');
  return body;
}

// --- Navigation Tabs ---
const NAV_ITEMS = [
  ['Overview', LayoutDashboard],
  ['My Agents', Bot],
  ['Knowledge Base', Database],
  ['Playground', MessageSquare],
  ['Training Studio', FlaskConical],
  ['Evaluations', Activity],
  ['Prompt Optimizer', Sparkles],
  ['Deployments', Globe],
  ['Analytics', BarChart3],
  ['Settings', Settings],
] as const;

// ==============================================================================
// ROOT APPLICATION
// ==============================================================================

function App() {
  const token = localStorage.getItem('agenttrainer_token');
  const [user, setUser] = useState<User>();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWs, setActiveWs] = useState<Workspace>();
  const [page, setPage] = useState<string>('Overview');
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    if (token) bootstrap();
    else setLoading(false);
  }, [token]);

  async function bootstrap() {
    try {
      const [me, wsList] = await Promise.all([api('/me'), api('/workspaces')]);
      setUser(me);
      setWorkspaces(wsList);
      const ws = wsList[0];
      setActiveWs(ws);
      if (ws) {
        const ags = await api(`/workspaces/${ws.id}/agents`);
        setAgents(ags);
      }
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  }

  const showToast = (msg: string, type: 'success' | 'error' = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4500);
  };

  const refreshAgents = async () => {
    if (!activeWs) return;
    const ags = await api(`/workspaces/${activeWs.id}/agents`);
    setAgents(ags);
  };

  if (loading) {
    return (
      <div className="auth-container">
        <div style={{ fontFamily: 'var(--font-display)', fontSize: '24px', letterSpacing: '0.04em' }}>
          AGENTTRAINER STUDIO <span style={{ color: 'var(--secondary)' }}>//</span> LOADING
        </div>
      </div>
    );
  }

  if (!token) {
    return <AuthView onAuthSuccess={() => location.reload()} onError={(m) => showToast(m, 'error')} />;
  }

  return (
    <div className="app">
      {/* Editorial Sidebar */}
      <aside className="sidebar">
        <div className="brand">
          <div style={{ width: 14, height: 14, background: 'var(--secondary)' }} />
          <span className="brand-title">AgentTrainer</span>
          <span className="brand-badge">PRO</span>
        </div>

        {/* Workspace Card */}
        <div className="workspace-card">
          <div className="avatar" style={{ width: 32, height: 32, background: 'var(--primary)', color: 'var(--tertiary)', display: 'grid', placeItems: 'center', fontWeight: 700 }}>
            {(activeWs?.name || 'W')[0]}
          </div>
          <div>
            <b>{activeWs?.name || 'Workspace'}</b>
            <small>{user?.email}</small>
          </div>
        </div>

        {/* Navigation */}
        <nav>
          {NAV_ITEMS.map(([label, Icon]) => (
            <button
              key={label}
              className={`nav-item ${page === label ? 'active' : ''}`}
              onClick={() => setPage(label)}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </nav>

        {/* Editorial Footer */}
        <div className="side-footer">
          <div className="usage-meter">
            <small>WORKSPACE AGENTS: {agents.length} / 20</small>
            <div className="meter-track">
              <div className="meter-fill" style={{ width: `${Math.min(100, agents.length * 5)}%` }} />
            </div>
          </div>
          <button
            className="user-profile-btn"
            onClick={() => {
              localStorage.removeItem('agenttrainer_token');
              location.reload();
            }}
          >
            <div className="avatar" style={{ width: 28, height: 28, background: 'var(--surface-raised)', display: 'grid', placeItems: 'center', fontWeight: 700 }}>
              {(user?.full_name || 'U')[0]}
            </div>
            <div>
              <b>{user?.full_name || 'Account'}</b>
              <small>SIGN OUT</small>
            </div>
            <LogOut size={14} style={{ marginLeft: 'auto', color: 'var(--text-secondary)' }} />
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main>
        <header>
          <div className="header-left">
            <div className="header-crumb">
              AGENTTRAINER <span>/</span> {page}
            </div>
          </div>
          <div className="header-right">
            <span className="status-chip status-neutral">LIVE WORKSPACE</span>
          </div>
        </header>

        {toast && (
          <div
            style={{
              position: 'fixed',
              top: 24,
              right: 24,
              zIndex: 999,
              background: toast.type === 'error' ? 'var(--secondary)' : 'var(--primary)',
              color: '#FFFFFF',
              padding: '12px 20px',
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              border: '2px solid #000000',
            }}
          >
            <AlertCircle size={15} />
            {toast.msg}
          </div>
        )}

        <section className="main-content">
          {page === 'Overview' && (
            <OverviewView
              workspace={activeWs!}
              agents={agents}
              onNavigate={setPage}
              onRefresh={refreshAgents}
            />
          )}
          {page === 'My Agents' && (
            <AgentsView
              workspace={activeWs!}
              agents={agents}
              onRefresh={refreshAgents}
              showToast={showToast}
              onSelectPlayground={() => setPage('Playground')}
            />
          )}
          {page === 'Knowledge Base' && (
            <KnowledgeBaseView workspace={activeWs!} showToast={showToast} />
          )}
          {page === 'Playground' && (
            <PlaygroundView workspace={activeWs!} agents={agents} showToast={showToast} />
          )}
          {page === 'Training Studio' && (
            <TrainingStudioView workspace={activeWs!} showToast={showToast} />
          )}
          {page === 'Evaluations' && (
            <EvaluationsView workspace={activeWs!} agents={agents} showToast={showToast} />
          )}
          {page === 'Prompt Optimizer' && (
            <PromptOptimizerView
              workspace={activeWs!}
              agents={agents}
              showToast={showToast}
              onRefreshAgents={refreshAgents}
            />
          )}
          {page === 'Deployments' && (
            <DeploymentsView workspace={activeWs!} agents={agents} showToast={showToast} />
          )}
          {page === 'Analytics' && <AnalyticsView workspace={activeWs!} showToast={showToast} />}
          {page === 'Settings' && (
            <SettingsView user={user!} workspace={activeWs!} showToast={showToast} />
          )}
        </section>
      </main>
    </div>
  );
}

// ==============================================================================
// 1. AUTH VIEW
// ==============================================================================

function AuthView({ onAuthSuccess, onError }: { onAuthSuccess: () => void; onError: (m: string) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('register');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload = mode === 'login' ? { email, password } : { email, full_name: fullName, password };
      const res = await api(`/auth/${mode}`, { method: 'POST', body: JSON.stringify(payload) });
      localStorage.setItem('agenttrainer_token', res.access_token);
      onAuthSuccess();
    } catch (err: any) {
      onError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 16, height: 16, background: 'var(--secondary)' }} />
          <span style={{ fontFamily: 'var(--font-display)', fontSize: '18px', textTransform: 'uppercase' }}>
            AgentTrainer
          </span>
        </div>
        <h1>{mode === 'login' ? 'Sign into Studio.' : 'Create Workspace.'}</h1>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
          {mode === 'login'
            ? 'Access your agents, evaluations, and production deployments.'
            : 'Deploy rigorous, evaluated, and production-ready AI agents.'}
        </p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {mode === 'register' && (
            <div className="input-group">
              <label className="input-label">Full Name</label>
              <input
                className="input-text"
                placeholder="Eleanor Vance"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />
            </div>
          )}
          <div className="input-group">
            <label className="input-label">Work Email</label>
            <input
              type="email"
              className="input-text"
              placeholder="director@publication.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="input-group">
            <label className="input-label">Password</label>
            <input
              type="password"
              className="input-text"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
          </div>

          <button className="btn-primary" type="submit" disabled={submitting} style={{ marginTop: 8 }}>
            {submitting ? 'Authenticating…' : mode === 'login' ? 'Sign In' : 'Initialize Workspace'}
            <ArrowUpRight size={16} />
          </button>
        </form>

        <div style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <button
            className="btn-ghost btn-sm"
            onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
          >
            {mode === 'login' ? 'Need an account? Register workspace' : 'Existing member? Sign In'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ==============================================================================
// 2. OVERVIEW VIEW
// ==============================================================================

function OverviewView({
  workspace,
  agents,
  onNavigate,
  onRefresh,
}: {
  workspace: Workspace;
  agents: Agent[];
  onNavigate: (page: string) => void;
  onRefresh: () => void;
}) {
  const activeCount = agents.filter((a) => a.status === 'active').length;

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-head-eyebrow">EDITORIAL DISPATCH // WORKSPACE SUMMARY</div>
          <h1 className="page-head-title">The State of Intelligence.</h1>
          <p className="page-head-sub">
            Maintain total oversight over prompt versions, retrieval coverage, and evaluation benchmarks.
          </p>
        </div>
        <button className="btn-primary" onClick={() => onNavigate('My Agents')}>
          <Plus size={16} /> Create Agent
        </button>
      </div>

      {/* Stats Strip */}
      <div className="stats-strip">
        <div className="stat-cell">
          <div className="stat-label">Configured Agents</div>
          <div className="stat-value">{agents.length}</div>
          <div className="stat-sub">Defined in this workspace</div>
        </div>
        <div className="stat-cell">
          <div className="stat-label">Active / Published</div>
          <div className="stat-value">{activeCount}</div>
          <div className="stat-sub">Ready for runtime execution</div>
        </div>
        <div className="stat-cell">
          <div className="stat-label">Model Engine</div>
          <div className="stat-value">GPT-4o</div>
          <div className="stat-sub">Production default provider</div>
        </div>
        <div className="stat-cell">
          <div className="stat-label">Safety Benchmark</div>
          <div className="stat-value">100%</div>
          <div className="stat-sub">Zero security breaches recorded</div>
        </div>
      </div>

      {/* Editorial Pull Quote */}
      <div className="pull-quote">
        "An AI agent without rigorous evaluation is merely an opinion machine. Ground your models in verified workspace documents and test every revision against objective criteria."
      </div>

      {/* Active Agents Grid */}
      <div style={{ marginTop: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '20px', textTransform: 'uppercase' }}>
            Active Roster
          </h2>
          <button className="btn-ghost btn-sm" onClick={onRefresh}>
            <RefreshCw size={14} /> Sync
          </button>
        </div>

        {agents.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '48px 24px' }}>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', textTransform: 'uppercase', marginBottom: 8 }}>
              No Agents Configured
            </h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 20 }}>
              Launch your first specialized editorial or analytical agent.
            </p>
            <button className="btn-primary" onClick={() => onNavigate('My Agents')}>
              <Plus size={16} /> Configure Agent
            </button>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 20 }}>
            {agents.map((ag) => (
              <div key={ag.id} className="card-elevated" style={{ display: 'flex', flexDirection: 'column' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
                  <div>
                    <span className="chip" style={{ fontSize: '10px', padding: '2px 8px', marginBottom: 6 }}>
                      {ag.category.toUpperCase()}
                    </span>
                    <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', textTransform: 'uppercase' }}>
                      {ag.name}
                    </h3>
                  </div>
                  <span className={`status-chip ${ag.status === 'active' ? 'status-success' : 'status-warning'}`}>
                    {ag.status}
                  </span>
                </div>

                <p style={{ color: 'var(--text-secondary)', fontSize: '13px', flex: 1, marginBottom: 16 }}>
                  {ag.description || 'No summary specified.'}
                </p>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: 12 }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>
                    REV. v{ag.current_version} // {ag.model}
                  </span>
                  <button className="btn-secondary btn-sm" onClick={() => onNavigate('Playground')}>
                    Interact <ArrowUpRight size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

// ==============================================================================
// 3. AGENTS VIEW & BUILDER
// ==============================================================================

function AgentsView({
  workspace,
  agents,
  onRefresh,
  showToast,
  onSelectPlayground,
}: {
  workspace: Workspace;
  agents: Agent[];
  onRefresh: () => void;
  showToast: (msg: string, type?: 'success' | 'error') => void;
  onSelectPlayground: () => void;
}) {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [publishingAgent, setPublishingAgent] = useState<Agent | null>(null);
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    return agents.filter((a) =>
      `${a.name} ${a.description} ${a.category}`.toLowerCase().includes(search.toLowerCase())
    );
  }, [agents, search]);

  const handleDuplicate = async (agent: Agent) => {
    try {
      await api(`/workspaces/${workspace.id}/agents/${agent.id}/duplicate`, { method: 'POST' });
      showToast(`Duplicated ${agent.name}`);
      onRefresh();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleDelete = async (agent: Agent) => {
    if (!confirm(`Permanently remove agent "${agent.name}"?`)) return;
    try {
      await api(`/workspaces/${workspace.id}/agents/${agent.id}`, { method: 'DELETE' });
      showToast(`Deleted ${agent.name}`);
      onRefresh();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-head-eyebrow">AGENT DIRECTORY // BUILDER & CONFIG</div>
          <h1 className="page-head-title">Agent Architectures.</h1>
          <p className="page-head-sub">
            Construct, version, and duplicate specialized AI copilots with tailored instructions and grounding.
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
          <Plus size={16} /> New Agent
        </button>
      </div>

      <div style={{ display: 'flex', gap: 16, marginBottom: 24, alignItems: 'center' }}>
        <div style={{ position: 'relative', width: 340 }}>
          <input
            className="input-text"
            placeholder="FILTER BY NAME OR CATEGORY..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-secondary)' }}>
          SHOWING {filtered.length} OF {agents.length} AGENTS
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {filtered.map((ag) => (
          <div
            key={ag.id}
            className="card"
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '18px 24px' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
              <div
                style={{
                  width: 44,
                  height: 44,
                  background: 'var(--primary)',
                  color: '#FFFFFF',
                  display: 'grid',
                  placeItems: 'center',
                  fontFamily: 'var(--font-display)',
                  fontSize: '18px',
                }}
              >
                {ag.name[0]}
              </div>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <b style={{ fontSize: '16px', textTransform: 'uppercase' }}>{ag.name}</b>
                  <span className={`status-chip ${ag.status === 'active' ? 'status-success' : 'status-neutral'}`}>
                    {ag.status}
                  </span>
                  <span className="chip" style={{ fontSize: '10px', padding: '2px 8px' }}>
                    v{ag.current_version}
                  </span>
                </div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginTop: 4 }}>
                  {ag.description || 'No description provided.'}
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <button className="btn-secondary btn-sm" onClick={() => setEditingAgent(ag)}>
                Inspect
              </button>
              <button className="btn-secondary btn-sm" onClick={() => setPublishingAgent(ag)}>
                Publish Revision
              </button>
              <button className="btn-secondary btn-sm" onClick={() => handleDuplicate(ag)} title="Duplicate">
                <Copy size={14} />
              </button>
              <button className="btn-destructive btn-sm" onClick={() => handleDelete(ag)} title="Delete">
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {showCreateModal && (
        <AgentBuilderModal
          workspace={workspace}
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            onRefresh();
            showToast('Created agent successfully');
          }}
        />
      )}

      {editingAgent && (
        <AgentEditModal
          workspace={workspace}
          agent={editingAgent}
          onClose={() => setEditingAgent(null)}
          onSuccess={() => {
            setEditingAgent(null);
            onRefresh();
            showToast('Saved agent changes');
          }}
        />
      )}

      {publishingAgent && (
        <PublishVersionModal
          workspace={workspace}
          agent={publishingAgent}
          onClose={() => setPublishingAgent(null)}
          onSuccess={(ver) => {
            setPublishingAgent(null);
            onRefresh();
            showToast(`Published revision v${ver}`);
          }}
        />
      )}
    </>
  );
}

// --- Agent Builder Modal (Multi-step editorial wizard) ---
function AgentBuilderModal({
  workspace,
  onClose,
  onSuccess,
}: {
  workspace: Workspace;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [step, setStep] = useState(1);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('editorial');
  const [model, setModel] = useState('gpt-4o-mini');
  const [temperature, setTemperature] = useState(0.2);
  const [systemPrompt, setSystemPrompt] = useState('You are an authoritative editorial AI copilot.');
  const [personality, setPersonality] = useState('Direct, erudite, razor-sharp');
  const [restrictions, setRestrictions] = useState('Do not extrapolate beyond verified knowledge sources.');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api(`/workspaces/${workspace.id}/agents`, {
        method: 'POST',
        body: JSON.stringify({
          name,
          description,
          category,
          model,
          temperature,
          system_prompt: systemPrompt,
          personality,
          restrictions,
          status: 'active',
        }),
      });
      onSuccess();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-box">
        <div className="modal-header">
          <h3>ARCHITECT AGENT // STEP {step} OF 3</h3>
          <button className="btn-ghost btn-sm" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {step === 1 && (
              <>
                <div className="input-group">
                  <label className="input-label">Agent Nomenclature (Name)</label>
                  <input
                    className="input-text"
                    placeholder="E.g. Culture Columnist"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Editorial Focus / Description</label>
                  <textarea
                    className="textarea-input"
                    placeholder="What specific tasks or analysis does this agent own?"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Category</label>
                  <select
                    className="select-input"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                  >
                    <option value="editorial">Editorial / Commentary</option>
                    <option value="research">Technical Research</option>
                    <option value="support">Customer Support</option>
                    <option value="evaluation">Verification & Review</option>
                  </select>
                </div>
              </>
            )}

            {step === 2 && (
              <>
                <div className="input-group">
                  <label className="input-label">Foundation Model Engine</label>
                  <select className="select-input" value={model} onChange={(e) => setModel(e.target.value)}>
                    <option value="gpt-4o-mini">OpenAI GPT-4o Mini (High Speed)</option>
                    <option value="gpt-4o">OpenAI GPT-4o (Maximum Reasoning)</option>
                    <option value="gemini-1.5-pro">Google Gemini 1.5 Pro</option>
                    <option value="mock-deterministic">Internal Deterministic Mock</option>
                  </select>
                </div>
                <div className="input-group">
                  <label className="input-label">Sampling Temperature: {temperature}</label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={temperature}
                    onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  />
                  <span className="input-helper">Lower temperatures produce strict, repeatable outputs.</span>
                </div>
              </>
            )}

            {step === 3 && (
              <>
                <div className="input-group">
                  <label className="input-label">System Instructions</label>
                  <textarea
                    className="textarea-input"
                    rows={4}
                    value={systemPrompt}
                    onChange={(e) => setSystemPrompt(e.target.value)}
                    required
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Tone & Personality</label>
                  <input
                    className="input-text"
                    value={personality}
                    onChange={(e) => setPersonality(e.target.value)}
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Negative Restrictions</label>
                  <input
                    className="input-text"
                    value={restrictions}
                    onChange={(e) => setRestrictions(e.target.value)}
                  />
                </div>
              </>
            )}
          </div>

          <div className="modal-footer">
            {step > 1 && (
              <button className="btn-secondary" type="button" onClick={() => setStep(step - 1)}>
                Back
              </button>
            )}
            {step < 3 ? (
              <button
                className="btn-primary"
                type="button"
                disabled={step === 1 && !name.trim()}
                onClick={() => setStep(step + 1)}
              >
                Next Step
              </button>
            ) : (
              <button className="btn-primary" type="submit" disabled={submitting}>
                {submitting ? 'Constructing…' : 'Finalize & Build'}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

// --- Agent Edit Modal ---
function AgentEditModal({
  workspace,
  agent,
  onClose,
  onSuccess,
}: {
  workspace: Workspace;
  agent: Agent;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [name, setName] = useState(agent.name);
  const [description, setDescription] = useState(agent.description);
  const [status, setStatus] = useState(agent.status);
  const [systemPrompt, setSystemPrompt] = useState(agent.system_prompt);
  const [personality, setPersonality] = useState(agent.personality || '');
  const [restrictions, setRestrictions] = useState(agent.restrictions || '');
  const [saving, setSaving] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api(`/workspaces/${workspace.id}/agents/${agent.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          name,
          description,
          status,
          system_prompt: systemPrompt,
          personality,
          restrictions,
        }),
      });
      onSuccess();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-box">
        <div className="modal-header">
          <h3>INSPECT // {agent.name.toUpperCase()}</h3>
          <button className="btn-ghost btn-sm" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <form onSubmit={handleSave}>
          <div className="modal-body">
            <div className="input-group">
              <label className="input-label">Name</label>
              <input className="input-text" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="input-group">
              <label className="input-label">Lifecycle Status</label>
              <select className="select-input" value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="draft">Draft (Private development)</option>
                <option value="active">Active (Production ready)</option>
                <option value="paused">Paused (Temporarily disabled)</option>
                <option value="archived">Archived</option>
              </select>
            </div>
            <div className="input-group">
              <label className="input-label">System Instructions</label>
              <textarea
                className="textarea-input"
                rows={5}
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                required
              />
            </div>
            <div className="input-group">
              <label className="input-label">Personality</label>
              <input className="input-text" value={personality} onChange={(e) => setPersonality(e.target.value)} />
            </div>
            <div className="input-group">
              <label className="input-label">Restrictions</label>
              <input className="input-text" value={restrictions} onChange={(e) => setRestrictions(e.target.value)} />
            </div>
          </div>
          <div className="modal-footer">
            <button className="btn-secondary" type="button" onClick={onClose}>
              Cancel
            </button>
            <button className="btn-primary" type="submit" disabled={saving}>
              {saving ? 'Saving…' : 'Save Adjustments'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// --- Publish Version Modal ---
function PublishVersionModal({
  workspace,
  agent,
  onClose,
  onSuccess,
}: {
  workspace: Workspace;
  agent: Agent;
  onClose: () => void;
  onSuccess: (ver: number) => void;
}) {
  const [summary, setSummary] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await api(`/workspaces/${workspace.id}/agents/${agent.id}/publish`, {
        method: 'POST',
        body: JSON.stringify({ change_summary: summary }),
      });
      onSuccess(res.version_number);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-box">
        <div className="modal-header">
          <h3>PUBLISH REVISION // BUMP TO v{agent.current_version + 1}</h3>
          <button className="btn-ghost btn-sm" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <p style={{ color: 'var(--text-secondary)' }}>
              Publishing creates an immutable configuration snapshot that can be evaluated, deployed, or rolled back at any time.
            </p>
            <div className="input-group">
              <label className="input-label">Changelog / Release Summary</label>
              <textarea
                className="textarea-input"
                placeholder="What changed in this revision? E.g. Tuned prompt constraints and added style guide references."
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                required
              />
            </div>
          </div>
          <div className="modal-footer">
            <button className="btn-secondary" type="button" onClick={onClose}>
              Cancel
            </button>
            <button className="btn-primary" type="submit" disabled={submitting}>
              {submitting ? 'Publishing…' : 'Publish Snapshot'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ==============================================================================
// 4. KNOWLEDGE BASE & RAG
// ==============================================================================

function KnowledgeBaseView({
  workspace,
  showToast,
}: {
  workspace: Workspace;
  showToast: (m: string, t?: 'success' | 'error') => void;
}) {
  const [kbList, setKbList] = useState<KnowledgeBase[]>([]);
  const [selectedKb, setSelectedKb] = useState<KnowledgeBase | null>(null);
  const [showCreateKb, setShowCreateKb] = useState(false);
  const [newKbName, setNewKbName] = useState('');
  const [newKbDesc, setNewKbDesc] = useState('');
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    loadKnowledgeBases();
  }, [workspace]);

  const loadKnowledgeBases = async () => {
    try {
      const data = await api(`/workspaces/${workspace.id}/knowledge-bases`);
      setKbList(data);
      if (data.length && !selectedKb) setSelectedKb(data[0]);
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleCreateKb = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api(`/workspaces/${workspace.id}/knowledge-bases`, {
        method: 'POST',
        body: JSON.stringify({ name: newKbName, description: newKbDesc }),
      });
      setShowCreateKb(false);
      setNewKbName('');
      setNewKbDesc('');
      loadKnowledgeBases();
      setSelectedKb(res);
      showToast(`Created knowledge base: ${res.name}`);
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!selectedKb || !e.target.files?.length) return;
    const file = e.target.files[0];
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      await api(`/workspaces/${workspace.id}/knowledge-bases/${selectedKb.id}/documents`, {
        method: 'POST',
        body: formData,
      });
      showToast(`Processed and chunked "${file.name}"`);
      loadKnowledgeBases();
    } catch (err: any) {
      showToast(err.message, 'error');
    } finally {
      setUploading(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedKb || !searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await api(`/workspaces/${workspace.id}/knowledge-bases/${selectedKb.id}/retrieve`, {
        method: 'POST',
        body: JSON.stringify({ query: searchQuery, top_k: 4 }),
      });
      setSearchResults(res.chunks || []);
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setSearching(false);
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-head-eyebrow">RETRIEVAL AUGMENTED GENERATION // REPOSITORY</div>
          <h1 className="page-head-title">Knowledge Bases.</h1>
          <p className="page-head-sub">
            Ingest editorial guidelines, research papers, and technical manuals. Parsed into semantic embeddings for grounded citation.
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowCreateKb(true)}>
          <Plus size={16} /> New Knowledge Base
        </button>
      </div>

      <div className="split-pane">
        {/* Left Pane: Knowledge Bases List */}
        <div className="pane-left" style={{ padding: 20 }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '14px', textTransform: 'uppercase', marginBottom: 12 }}>
            Repositories ({kbList.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {kbList.map((kb) => (
              <button
                key={kb.id}
                className="card"
                style={{
                  textAlign: 'left',
                  padding: '12px 16px',
                  background: selectedKb?.id === kb.id ? 'var(--primary)' : '#FFFFFF',
                  color: selectedKb?.id === kb.id ? '#FFFFFF' : 'var(--text-primary)',
                  borderColor: selectedKb?.id === kb.id ? 'var(--primary)' : 'var(--border-medium)',
                }}
                onClick={() => setSelectedKb(kb)}
              >
                <b style={{ display: 'block', fontSize: '13px', textTransform: 'uppercase' }}>{kb.name}</b>
                <small style={{ color: selectedKb?.id === kb.id ? '#CCCCCC' : 'var(--text-secondary)' }}>
                  {kb.documents?.length || 0} documents parsed
                </small>
              </button>
            ))}
          </div>
        </div>

        {/* Right Pane: Selected KB Documents & Semantic Tester */}
        <div className="pane-right" style={{ padding: 32 }}>
          {selectedKb ? (
            <>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', borderBottom: '2px solid var(--border-strong)', paddingBottom: 20, marginBottom: 24 }}>
                <div>
                  <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', textTransform: 'uppercase' }}>
                    {selectedKb.name}
                  </h2>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: 4 }}>
                    {selectedKb.description || 'No description provided.'}
                  </p>
                </div>
                <label className="btn-primary" style={{ cursor: 'pointer' }}>
                  <Upload size={16} /> {uploading ? 'Processing Document…' : 'Upload File'}
                  <input
                    type="file"
                    accept=".txt,.md,.json,.csv,.pdf,.docx"
                    style={{ display: 'none' }}
                    onChange={handleFileUpload}
                    disabled={uploading}
                  />
                </label>
              </div>

              {/* Document List */}
              <div style={{ marginBottom: 32 }}>
                <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '16px', textTransform: 'uppercase', marginBottom: 12 }}>
                  Ingested Documents
                </h3>
                {selectedKb.documents && selectedKb.documents.length > 0 ? (
                  <div style={{ border: '2px solid var(--border-strong)' }}>
                    {selectedKb.documents.map((d) => (
                      <div
                        key={d.id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '12px 18px',
                          borderBottom: '1px solid var(--border-subtle)',
                          background: '#FFFFFF',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                          <FileText size={18} style={{ color: 'var(--secondary)' }} />
                          <div>
                            <b style={{ fontSize: '14px' }}>{d.name}</b>
                            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                              FORMAT: {d.file_type.toUpperCase()} // SIZE: {Math.round(d.file_size / 1024)} KB // {d.chunk_count} CHUNKS
                            </div>
                          </div>
                        </div>
                        <span className="status-chip status-success">GROUNDED & READY</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="card" style={{ textAlign: 'center', padding: '32px' }}>
                    <p style={{ color: 'var(--text-secondary)' }}>
                      No documents ingested yet. Upload a .txt, .pdf, or .docx file to create searchable semantic chunks.
                    </p>
                  </div>
                )}
              </div>

              {/* Semantic Retrieval Inspector */}
              <div className="card" style={{ background: 'var(--surface)' }}>
                <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '16px', textTransform: 'uppercase', marginBottom: 8 }}>
                  Semantic Retrieval Tester
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: 16 }}>
                  Test vector and keyword similarity directly against this repository's partitioned chunks.
                </p>

                <form onSubmit={handleSearch} style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
                  <input
                    className="input-text"
                    placeholder="Enter query to inspect top-matching chunks..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  <button className="btn-primary" type="submit" disabled={searching}>
                    {searching ? 'Querying…' : 'Retrieve'}
                  </button>
                </form>

                {searchResults.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {searchResults.map((r, i) => (
                      <div
                        key={i}
                        style={{
                          background: '#FFFFFF',
                          border: '2px solid var(--border-strong)',
                          padding: 16,
                          borderLeft: '4px solid var(--secondary)',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                          <b style={{ fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
                            SOURCE: {r.document_name} // CHUNK #{r.chunk_index}
                          </b>
                          <span className="status-chip status-neutral">
                            RELEVANCE: {Math.round(r.score * 100)}%
                          </span>
                        </div>
                        <p style={{ fontSize: '13px', color: 'var(--text-primary)' }}>{r.content}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-secondary)' }}>
              Select or create a knowledge base to begin.
            </div>
          )}
        </div>
      </div>

      {showCreateKb && (
        <div className="modal-overlay">
          <div className="modal-box">
            <div className="modal-header">
              <h3>CREATE KNOWLEDGE REPOSITORY</h3>
              <button className="btn-ghost btn-sm" onClick={() => setShowCreateKb(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCreateKb}>
              <div className="modal-body">
                <div className="input-group">
                  <label className="input-label">Repository Name</label>
                  <input
                    className="input-text"
                    placeholder="E.g. Publications Style Guide 2026"
                    value={newKbName}
                    onChange={(e) => setNewKbName(e.target.value)}
                    required
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Description / Scope</label>
                  <textarea
                    className="textarea-input"
                    placeholder="What domain does this knowledge base cover?"
                    value={newKbDesc}
                    onChange={(e) => setNewKbDesc(e.target.value)}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button className="btn-secondary" type="button" onClick={() => setShowCreateKb(false)}>
                  Cancel
                </button>
                <button className="btn-primary" type="submit">
                  Create Repository
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

// ==============================================================================
// 5. PLAYGROUND & CHAT VIEW
// ==============================================================================

function PlaygroundView({
  workspace,
  agents,
  showToast,
}: {
  workspace: Workspace;
  agents: Agent[];
  showToast: (m: string, t?: 'success' | 'error') => void;
}) {
  const [selectedAgentId, setSelectedAgentId] = useState(agents[0]?.id || '');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConv, setActiveConv] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [inspectMessage, setInspectMessage] = useState<Message | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const selectedAgent = agents.find((a) => a.id === selectedAgentId);

  useEffect(() => {
    if (selectedAgentId) loadConversations(selectedAgentId);
  }, [selectedAgentId]);

  const loadConversations = async (agId: string) => {
    try {
      const data = await api(`/workspaces/${workspace.id}/agents/${agId}/conversations`);
      setConversations(data);
      if (data.length > 0) loadConversationDetails(data[0].id);
      else {
        setActiveConv(null);
        setMessages([]);
      }
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const loadConversationDetails = async (convId: string) => {
    try {
      const conv = await api(`/workspaces/${workspace.id}/conversations/${convId}`);
      setActiveConv(conv);
      setMessages(conv.messages || []);
      setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleNewConversation = async () => {
    if (!selectedAgentId) return;
    try {
      const conv = await api(`/workspaces/${workspace.id}/agents/${selectedAgentId}/conversations`, {
        method: 'POST',
        body: JSON.stringify({ title: 'New Conversation' }),
      });
      setConversations([conv, ...conversations]);
      setActiveConv(conv);
      setMessages([]);
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || sending) return;

    let convId = activeConv?.id;
    if (!convId) {
      const newConv = await api(`/workspaces/${workspace.id}/agents/${selectedAgentId}/conversations`, {
        method: 'POST',
        body: JSON.stringify({ title: input.slice(0, 30) }),
      });
      convId = newConv.id;
      setActiveConv(newConv);
      setConversations([newConv, ...conversations]);
    }

    const optimisticUserMsg: Message = {
      id: 'opt_' + Date.now(),
      role: 'user',
      content: input,
      citations_json: [],
      token_count: 0,
      latency_ms: 0,
      cost_est: 0,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticUserMsg]);
    const textToSend = input;
    setInput('');
    setSending(true);

    try {
      const assistantMsg = await api(`/workspaces/${workspace.id}/conversations/${convId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ content: textToSend }),
      });
      setMessages((prev) => [...prev, assistantMsg]);
      setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-head-eyebrow">RUNTIME ENVIRONMENT // INTERACTIVE TESTING</div>
          <h1 className="page-head-title">Playground Studio.</h1>
          <p className="page-head-sub">
            Engage with agents directly in real time. Inspect context assembly, grounding citations, and token consumption.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <select
            className="select-input"
            style={{ width: 220 }}
            value={selectedAgentId}
            onChange={(e) => setSelectedAgentId(e.target.value)}
          >
            {agents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} (v{a.current_version})
              </option>
            ))}
          </select>
          <button className="btn-primary" onClick={handleNewConversation}>
            <Plus size={16} /> New Chat
          </button>
        </div>
      </div>

      <div className="split-pane" style={{ height: 'calc(100vh - 280px)' }}>
        {/* Left Pane: Conversation History */}
        <div className="pane-left" style={{ padding: 16 }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '13px', textTransform: 'uppercase', marginBottom: 12 }}>
            Sessions ({conversations.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, overflowY: 'auto' }}>
            {conversations.map((c) => (
              <button
                key={c.id}
                className="card"
                style={{
                  textAlign: 'left',
                  padding: '10px 14px',
                  background: activeConv?.id === c.id ? 'var(--primary)' : '#FFFFFF',
                  color: activeConv?.id === c.id ? '#FFFFFF' : 'var(--text-primary)',
                  borderColor: activeConv?.id === c.id ? 'var(--primary)' : 'var(--border-subtle)',
                }}
                onClick={() => loadConversationDetails(c.id)}
              >
                <b style={{ fontSize: '13px', display: 'block', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                  {c.title || 'Untitled Session'}
                </b>
                <small style={{ color: activeConv?.id === c.id ? '#BBB' : 'var(--text-secondary)' }}>
                  {new Date(c.updated_at).toLocaleDateString()}
                </small>
              </button>
            ))}
          </div>
        </div>

        {/* Right Pane: Active Chat Exchange */}
        <div className="pane-right">
          <div className="chat-scroll">
            {messages.length === 0 ? (
              <div style={{ textAlign: 'center', margin: 'auto', maxWidth: 440 }}>
                <Bot size={36} style={{ color: 'var(--secondary)', marginBottom: 12 }} />
                <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '20px', textTransform: 'uppercase' }}>
                  {selectedAgent?.name || 'Agent Ready'}
                </h3>
                <p style={{ color: 'var(--text-secondary)', marginTop: 8 }}>
                  {selectedAgent?.personality || 'Prompt initialized. Begin dialogue to test retrieval and prompt bounds.'}
                </p>
              </div>
            ) : (
              messages.map((m) => (
                <div
                  key={m.id}
                  className={`msg-bubble ${m.role === 'user' ? 'msg-user' : 'msg-assistant'}`}
                >
                  <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', opacity: 0.7, marginBottom: 4, textTransform: 'uppercase' }}>
                    {m.role === 'user' ? 'Editorial Director' : `${selectedAgent?.name || 'Agent'} [v${selectedAgent?.current_version || 1}]`}
                  </div>
                  <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{m.content}</div>

                  {m.citations_json && m.citations_json.length > 0 && (
                    <div className="citations-box">
                      <b style={{ textTransform: 'uppercase', fontSize: '10px', letterSpacing: '0.06em' }}>
                        Retrieved Sources:
                      </b>
                      <div>
                        {m.citations_json.map((c, idx) => (
                          <span key={idx} className="citation-pill" title={c.snippet}>
                            [Doc: {c.source} #{c.chunk_index}] ({c.relevance}%)
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {m.role === 'assistant' && m.token_count > 0 && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 10, paddingTop: 6, borderTop: '1px solid var(--border-subtle)', fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                      <span>TOKENS: {m.token_count}</span>
                      <span>LATENCY: {m.latency_ms}ms</span>
                      <span>COST: ${m.cost_est}</span>
                      <button
                        style={{ marginLeft: 'auto', textDecoration: 'underline', color: 'var(--primary)' }}
                        onClick={() => setInspectMessage(m)}
                      >
                        Inspect Telemetry
                      </button>
                    </div>
                  )}
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input */}
          <form className="chat-input-row" onSubmit={handleSendMessage}>
            <input
              className="input-text"
              placeholder={`Query ${selectedAgent?.name || 'Agent'}...`}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={sending}
            />
            <button className="btn-primary" type="submit" disabled={sending || !input.trim()}>
              <Send size={15} /> {sending ? 'Executing…' : 'Send'}
            </button>
          </form>
        </div>
      </div>

      {inspectMessage && (
        <div className="modal-overlay">
          <div className="modal-box">
            <div className="modal-header">
              <h3>EXECUTION TELEMETRY & CONTEXT</h3>
              <button className="btn-ghost btn-sm" onClick={() => setInspectMessage(null)}>
                <X size={18} />
              </button>
            </div>
            <div className="modal-body">
              <pre>{JSON.stringify(inspectMessage.debug_json || inspectMessage, null, 2)}</pre>
            </div>
            <div className="modal-footer">
              <button className="btn-primary" onClick={() => setInspectMessage(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ==============================================================================
// 6. TRAINING STUDIO VIEW
// ==============================================================================

function TrainingStudioView({
  workspace,
  showToast,
}: {
  workspace: Workspace;
  showToast: (m: string, t?: 'success' | 'error') => void;
}) {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDs, setSelectedDs] = useState<Dataset | null>(null);
  const [newDsName, setNewDsName] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAddExModal, setShowAddExModal] = useState(false);
  const [showSyntheticModal, setShowSyntheticModal] = useState(false);
  const [kbList, setKbList] = useState<KnowledgeBase[]>([]);
  const [synthKbId, setSynthKbId] = useState('');
  const [synthCount, setSynthCount] = useState(5);
  const [generating, setGenerating] = useState(false);

  // New example inputs
  const [exQ, setExQ] = useState('');
  const [exAns, setExAns] = useState('');
  const [exCat, setExCat] = useState('general');

  useEffect(() => {
    loadDatasets();
    loadKbs();
  }, [workspace]);

  const loadDatasets = async () => {
    try {
      const data = await api(`/workspaces/${workspace.id}/datasets`);
      setDatasets(data);
      if (data.length && !selectedDs) setSelectedDs(data[0]);
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const loadKbs = async () => {
    try {
      const data = await api(`/workspaces/${workspace.id}/knowledge-bases`);
      setKbList(data);
      if (data.length) setSynthKbId(data[0].id);
    } catch (e: any) {}
  };

  const handleCreateDataset = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api(`/workspaces/${workspace.id}/datasets`, {
        method: 'POST',
        body: JSON.stringify({ name: newDsName, description: 'Evaluation and training set.' }),
      });
      setShowCreateModal(false);
      setNewDsName('');
      loadDatasets();
      setSelectedDs(res);
      showToast(`Created dataset: ${res.name}`);
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleAddExample = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDs) return;
    try {
      await api(`/workspaces/${workspace.id}/datasets/${selectedDs.id}/examples`, {
        method: 'POST',
        body: JSON.stringify({ question: exQ, expected_answer: exAns, category: exCat }),
      });
      setShowAddExModal(false);
      setExQ('');
      setExAns('');
      loadDatasets();
      showToast('Added example to dataset');
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleGenerateSynthetic = async () => {
    if (!selectedDs || !synthKbId) return;
    setGenerating(true);
    try {
      const res = await api(`/workspaces/${workspace.id}/datasets/${selectedDs.id}/generate-synthetic`, {
        method: 'POST',
        body: JSON.stringify({ knowledge_base_id: synthKbId, count: synthCount }),
      });
      setShowSyntheticModal(false);
      loadDatasets();
      showToast(`Synthesized ${res.generated_count} Q&A cases from knowledge base`);
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-head-eyebrow">TRAINING STUDIO // DATASET CURATION</div>
          <h1 className="page-head-title">Evaluation Datasets.</h1>
          <p className="page-head-sub">
            Assemble gold-standard test suites and synthetic example pairs to validate agent performance before release.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button className="btn-secondary" onClick={() => setShowSyntheticModal(true)} disabled={!selectedDs || !kbList.length}>
            <Sparkles size={16} /> Synthesize from Docs
          </button>
          <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
            <Plus size={16} /> New Dataset
          </button>
        </div>
      </div>

      <div className="split-pane">
        {/* Left Pane: Datasets List */}
        <div className="pane-left" style={{ padding: 20 }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '14px', textTransform: 'uppercase', marginBottom: 12 }}>
            Datasets ({datasets.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {datasets.map((ds) => (
              <button
                key={ds.id}
                className="card"
                style={{
                  textAlign: 'left',
                  padding: '12px 16px',
                  background: selectedDs?.id === ds.id ? 'var(--primary)' : '#FFFFFF',
                  color: selectedDs?.id === ds.id ? '#FFFFFF' : 'var(--text-primary)',
                  borderColor: selectedDs?.id === ds.id ? 'var(--primary)' : 'var(--border-medium)',
                }}
                onClick={() => setSelectedDs(ds)}
              >
                <b style={{ display: 'block', fontSize: '13px', textTransform: 'uppercase' }}>{ds.name}</b>
                <small style={{ color: selectedDs?.id === ds.id ? '#CCC' : 'var(--text-secondary)' }}>
                  {ds.examples?.length || 0} validation cases
                </small>
              </button>
            ))}
          </div>
        </div>

        {/* Right Pane: Dataset Examples */}
        <div className="pane-right" style={{ padding: 32 }}>
          {selectedDs ? (
            <>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '2px solid var(--border-strong)', paddingBottom: 16, marginBottom: 24 }}>
                <div>
                  <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '22px', textTransform: 'uppercase' }}>
                    {selectedDs.name}
                  </h2>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                    {selectedDs.examples?.length || 0} reference examples in this suite
                  </p>
                </div>
                <button className="btn-primary btn-sm" onClick={() => setShowAddExModal(true)}>
                  <Plus size={14} /> Add Test Example
                </button>
              </div>

              {selectedDs.examples && selectedDs.examples.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  {selectedDs.examples.map((ex, i) => (
                    <div key={ex.id || i} className="card" style={{ padding: 18 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                        <span className="chip" style={{ fontSize: '10px', padding: '2px 8px' }}>
                          CATEGORY: {ex.category.toUpperCase()}
                        </span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>
                          CASE #{i + 1}
                        </span>
                      </div>
                      <div style={{ marginBottom: 8 }}>
                        <b style={{ fontSize: '14px', color: 'var(--text-primary)' }}>Q: {ex.question}</b>
                      </div>
                      <div style={{ background: 'var(--surface)', padding: 12, borderLeft: '3px solid var(--primary)', fontSize: '13px' }}>
                        <b>Expected Answer:</b> {ex.expected_answer}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="card" style={{ textAlign: 'center', padding: 40 }}>
                  <p style={{ color: 'var(--text-secondary)' }}>
                    No examples curated yet. Add manual test cases or click "Synthesize from Docs" to generate them automatically.
                  </p>
                </div>
              )}
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-secondary)' }}>
              Select a dataset from the sidebar.
            </div>
          )}
        </div>
      </div>

      {/* Create Dataset Modal */}
      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal-box">
            <div className="modal-header">
              <h3>CREATE EVALUATION DATASET</h3>
              <button className="btn-ghost btn-sm" onClick={() => setShowCreateModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCreateDataset}>
              <div className="modal-body">
                <div className="input-group">
                  <label className="input-label">Dataset Name</label>
                  <input
                    className="input-text"
                    placeholder="E.g. Editorial Guidelines Q&A"
                    value={newDsName}
                    onChange={(e) => setNewDsName(e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button className="btn-secondary" type="button" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button className="btn-primary" type="submit">
                  Create Dataset
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Example Modal */}
      {showAddExModal && (
        <div className="modal-overlay">
          <div className="modal-box">
            <div className="modal-header">
              <h3>ADD REFERENCE TEST CASE</h3>
              <button className="btn-ghost btn-sm" onClick={() => setShowAddExModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleAddExample}>
              <div className="modal-body">
                <div className="input-group">
                  <label className="input-label">Test Question</label>
                  <textarea
                    className="textarea-input"
                    placeholder="What did the user ask?"
                    value={exQ}
                    onChange={(e) => setExQ(e.target.value)}
                    required
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Expected / Reference Answer</label>
                  <textarea
                    className="textarea-input"
                    rows={4}
                    placeholder="What specific facts and concepts must be included?"
                    value={exAns}
                    onChange={(e) => setExAns(e.target.value)}
                    required
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Category</label>
                  <input className="input-text" value={exCat} onChange={(e) => setExCat(e.target.value)} />
                </div>
              </div>
              <div className="modal-footer">
                <button className="btn-secondary" type="button" onClick={() => setShowAddExModal(false)}>
                  Cancel
                </button>
                <button className="btn-primary" type="submit">
                  Save Example
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Synthetic Generation Modal */}
      {showSyntheticModal && (
        <div className="modal-overlay">
          <div className="modal-box">
            <div className="modal-header">
              <h3>SYNTHESIZE DATASET FROM KNOWLEDGE BASE</h3>
              <button className="btn-ghost btn-sm" onClick={() => setShowSyntheticModal(false)}>
                <X size={18} />
              </button>
            </div>
            <div className="modal-body">
              <p style={{ color: 'var(--text-secondary)' }}>
                Automatically extracts factual statements from your ingested documents and generates grounded Q&A pairs for benchmark evaluation.
              </p>
              <div className="input-group">
                <label className="input-label">Target Knowledge Base</label>
                <select className="select-input" value={synthKbId} onChange={(e) => setSynthKbId(e.target.value)}>
                  {kbList.map((kb) => (
                    <option key={kb.id} value={kb.id}>
                      {kb.name} ({kb.documents?.length || 0} docs)
                    </option>
                  ))}
                </select>
              </div>
              <div className="input-group">
                <label className="input-label">Number of Cases to Synthesize: {synthCount}</label>
                <input
                  type="range"
                  min="2"
                  max="15"
                  value={synthCount}
                  onChange={(e) => setSynthCount(parseInt(e.target.value))}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" type="button" onClick={() => setShowSyntheticModal(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleGenerateSynthetic} disabled={generating}>
                {generating ? 'Synthesizing…' : 'Generate Q&A Pairs'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ==============================================================================
// 7. EVALUATIONS VIEW
// ==============================================================================

function EvaluationsView({
  workspace,
  agents,
  showToast,
}: {
  workspace: Workspace;
  agents: Agent[];
  showToast: (m: string, t?: 'success' | 'error') => void;
}) {
  const [tab, setTab] = useState<'single' | 'batch' | 'history'>('single');
  const [agentId, setAgentId] = useState(agents[0]?.id || '');
  const [question, setQuestion] = useState('');
  const [expectedAnswer, setExpectedAnswer] = useState('');
  const [actualAnswer, setActualAnswer] = useState('');
  const [evalResult, setEvalResult] = useState<EvaluationResult | null>(null);
  const [evaluating, setEvaluating] = useState(false);

  // Batch
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [datasetId, setDatasetId] = useState('');
  const [batchRun, setBatchRun] = useState<EvaluationRun | null>(null);

  // History
  const [historyRuns, setHistoryRuns] = useState<EvaluationRun[]>([]);

  useEffect(() => {
    loadDatasets();
    loadRuns();
  }, [workspace]);

  const loadDatasets = async () => {
    try {
      const data = await api(`/workspaces/${workspace.id}/datasets`);
      setDatasets(data);
      if (data.length) setDatasetId(data[0].id);
    } catch (e: any) {}
  };

  const loadRuns = async () => {
    try {
      const data = await api(`/workspaces/${workspace.id}/evaluations/runs`);
      setHistoryRuns(data);
    } catch (e: any) {}
  };

  const handleSingleEval = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agentId) return;
    setEvaluating(true);
    try {
      const res = await api(`/workspaces/${workspace.id}/evaluations`, {
        method: 'POST',
        body: JSON.stringify({
          agent_id: agentId,
          question,
          expected_answer: expectedAnswer,
          actual_answer: actualAnswer,
        }),
      });
      setEvalResult(res);
      loadRuns();
      showToast(`Evaluation completed: ${res.overall_score}% (${res.grade})`);
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setEvaluating(false);
    }
  };

  const handleBatchEval = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agentId || !datasetId) return;
    setEvaluating(true);
    try {
      const res = await api(`/workspaces/${workspace.id}/evaluations/batch`, {
        method: 'POST',
        body: JSON.stringify({ agent_id: agentId, dataset_id: datasetId }),
      });
      setBatchRun(res);
      loadRuns();
      showToast(`Batch evaluation completed across dataset: ${res.overall_score}%`);
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-head-eyebrow">METRICS & BENCHMARKS // SCORING ENGINE</div>
          <h1 className="page-head-title">Evaluation Engine.</h1>
          <p className="page-head-sub">
            Measure agent accuracy, relevance, completeness, hallucination risk, and safety against verified reference answers.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className={tab === 'single' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
            onClick={() => setTab('single')}
          >
            Single Response
          </button>
          <button
            className={tab === 'batch' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
            onClick={() => setTab('batch')}
          >
            Batch Suite Run
          </button>
          <button
            className={tab === 'history' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
            onClick={() => setTab('history')}
          >
            Run History ({historyRuns.length})
          </button>
        </div>
      </div>

      {tab === 'single' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
          {/* Form */}
          <form className="card" onSubmit={handleSingleEval}>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', textTransform: 'uppercase', marginBottom: 16 }}>
              Run Single Case Evaluation
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div className="input-group">
                <label className="input-label">Agent to Evaluate</label>
                <select className="select-input" value={agentId} onChange={(e) => setAgentId(e.target.value)}>
                  {agents.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name} (v{a.current_version})
                    </option>
                  ))}
                </select>
              </div>
              <div className="input-group">
                <label className="input-label">User Query / Question</label>
                <textarea
                  className="textarea-input"
                  placeholder="What was the user prompt?"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  required
                />
              </div>
              <div className="input-group">
                <label className="input-label">Expected Reference Answer</label>
                <textarea
                  className="textarea-input"
                  placeholder="What exact concepts, numbers, or rules must be present?"
                  value={expectedAnswer}
                  onChange={(e) => setExpectedAnswer(e.target.value)}
                  required
                />
              </div>
              <div className="input-group">
                <label className="input-label">Actual Agent Response</label>
                <textarea
                  className="textarea-input"
                  rows={4}
                  placeholder="Paste or enter the response to evaluate..."
                  value={actualAnswer}
                  onChange={(e) => setActualAnswer(e.target.value)}
                  required
                />
              </div>
              <button className="btn-primary" type="submit" disabled={evaluating}>
                {evaluating ? 'Analyzing Alignment…' : 'Compute Score Breakdown'}
              </button>
            </div>
          </form>

          {/* Results Card */}
          <div className="card-elevated">
            {evalResult ? (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '2px solid var(--border-strong)', paddingBottom: 16, marginBottom: 20 }}>
                  <div>
                    <span className="page-head-eyebrow">BENCHMARK RATING</span>
                    <div style={{ fontFamily: 'var(--font-display)', fontSize: '48px', color: 'var(--primary)', lineHeight: 1 }}>
                      {evalResult.overall_score}%
                    </div>
                  </div>
                  <span className={`status-chip ${evalResult.overall_score >= 80 ? 'status-success' : 'status-warning'}`} style={{ fontSize: '14px', padding: '6px 16px' }}>
                    {evalResult.grade}
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 24 }}>
                  {[
                    ['Accuracy & Entity Match', evalResult.accuracy],
                    ['Relevance & Intent', evalResult.relevance],
                    ['Completeness & Coverage', evalResult.completeness],
                    ['Instruction Compliance', evalResult.instruction_following],
                    ['Unsupported Content (Hallucination)', evalResult.hallucination_risk],
                    ['Safety & Defense Check', evalResult.safety],
                  ].map(([name, dim]: any) => (
                    <div key={name}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: 700, marginBottom: 4 }}>
                        <span>{name}</span>
                        <span style={{ fontFamily: 'var(--font-mono)' }}>{dim.score}%</span>
                      </div>
                      <div className="meter-track" style={{ height: 6 }}>
                        <div
                          className="meter-fill"
                          style={{
                            width: `${dim.score}%`,
                            background: dim.score >= 70 ? 'var(--primary)' : 'var(--secondary)',
                          }}
                        />
                      </div>
                      <small style={{ color: 'var(--text-secondary)', fontSize: '11px', display: 'block', marginTop: 2 }}>
                        {dim.feedback}
                      </small>
                    </div>
                  ))}
                </div>

                <div style={{ borderTop: '2px solid var(--border-subtle)', paddingTop: 16 }}>
                  <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '14px', textTransform: 'uppercase', marginBottom: 8 }}>
                    Actionable Recommendations
                  </h4>
                  {evalResult.suggestions.map((s, i) => (
                    <div key={i} style={{ display: 'flex', gap: 8, fontSize: '13px', color: 'var(--text-secondary)', marginBottom: 6 }}>
                      <span style={{ color: 'var(--secondary)', fontWeight: 700 }}>→</span>
                      <span>{s}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-secondary)' }}>
                <Activity size={36} style={{ color: 'var(--secondary)', marginBottom: 12 }} />
                <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', textTransform: 'uppercase' }}>
                  Awaiting Evaluation Case
                </h3>
                <p style={{ marginTop: 8 }}>
                  Submit the form on the left to measure alignment against the VoiceBox baseline.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'batch' && (
        <div className="card">
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '20px', textTransform: 'uppercase', marginBottom: 16 }}>
            Run Batch Suite Evaluation
          </h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 20 }}>
            Executes all examples in your selected dataset through the agent, scoring every test case and calculating aggregate performance.
          </p>

          <form onSubmit={handleBatchEval} style={{ display: 'flex', gap: 16, alignItems: 'flex-end', marginBottom: 24 }}>
            <div className="input-group" style={{ width: 260 }}>
              <label className="input-label">Select Agent</label>
              <select className="select-input" value={agentId} onChange={(e) => setAgentId(e.target.value)}>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name} (v{a.current_version})
                  </option>
                ))}
              </select>
            </div>
            <div className="input-group" style={{ width: 260 }}>
              <label className="input-label">Select Test Dataset</label>
              <select className="select-input" value={datasetId} onChange={(e) => setDatasetId(e.target.value)}>
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.examples?.length || 0} cases)
                  </option>
                ))}
              </select>
            </div>
            <button className="btn-primary" type="submit" disabled={evaluating}>
              {evaluating ? 'Running Suite…' : 'Execute Batch Evaluation'}
            </button>
          </form>

          {batchRun && (
            <div className="card-elevated" style={{ marginTop: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                <div>
                  <div className="page-head-eyebrow">BATCH RUN COMPLETED</div>
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '24px' }}>
                    AGGREGATE SCORE: {batchRun.overall_score}%
                  </h3>
                </div>
                <span className="status-chip status-success">{batchRun.grade}</span>
              </div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                Executed {batchRun.summary_json?.example_count || 'all'} test examples from suite "{batchRun.summary_json?.dataset_name}". Detailed run record persisted to durable history.
              </p>
            </div>
          )}
        </div>
      )}

      {tab === 'history' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {historyRuns.length > 0 ? (
            historyRuns.map((r) => (
              <div key={r.id} className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <b style={{ fontSize: '16px' }}>SCORE: {r.overall_score}%</b>
                    <span className="status-chip status-neutral">REV. v{r.agent_version}</span>
                    <span className="chip" style={{ fontSize: '10px', padding: '2px 8px' }}>{r.grade}</span>
                  </div>
                  <small style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                    RUN ID: {r.id.slice(0, 12)} // DATE: {new Date(r.created_at).toLocaleString()}
                  </small>
                </div>
                <span className="status-chip status-success">PERSISTED</span>
              </div>
            ))
          ) : (
            <div className="card" style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary)' }}>
              No evaluation runs recorded yet.
            </div>
          )}
        </div>
      )}
    </>
  );
}

// ==============================================================================
// 8. PROMPT OPTIMIZER VIEW
// ==============================================================================

function PromptOptimizerView({
  workspace,
  agents,
  showToast,
  onRefreshAgents,
}: {
  workspace: Workspace;
  agents: Agent[];
  showToast: (m: string, t?: 'success' | 'error') => void;
  onRefreshAgents: () => void;
}) {
  const [selectedAgentId, setSelectedAgentId] = useState(agents[0]?.id || '');
  const [focusAreas, setFocusAreas] = useState<string[]>(['accuracy', 'grounding', 'conciseness']);
  const [optimizing, setOptimizing] = useState(false);
  const [optResult, setOptResult] = useState<any>(null);
  const [approving, setApproving] = useState(false);

  const selectedAgent = agents.find((a) => a.id === selectedAgentId);

  const toggleFocus = (area: string) => {
    setFocusAreas((prev) => (prev.includes(area) ? prev.filter((a) => a !== area) : [...prev, area]));
  };

  const handleGenerate = async () => {
    if (!selectedAgentId) return;
    setOptimizing(true);
    try {
      const res = await api(`/workspaces/${workspace.id}/prompt-optimizer/generate`, {
        method: 'POST',
        body: JSON.stringify({ agent_id: selectedAgentId, focus_areas: focusAreas }),
      });
      setOptResult(res);
      showToast('Generated prompt optimization candidate');
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setOptimizing(false);
    }
  };

  const handleApprove = async () => {
    if (!optResult) return;
    setApproving(true);
    try {
      await api(`/workspaces/${workspace.id}/prompt-optimizer/${optResult.id}/approve`, {
        method: 'POST',
      });
      showToast('Approved prompt optimization & published new agent version!');
      onRefreshAgents();
      setOptResult(null);
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setApproving(false);
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-head-eyebrow">AUTOMATED REFINEMENT // PROMPT OPTIMIZER</div>
          <h1 className="page-head-title">System Prompt Tuning.</h1>
          <p className="page-head-sub">
            Analyze weak failure cases and generate hardened, grounded prompt revisions with line-by-line diff inspections.
          </p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', textTransform: 'uppercase', marginBottom: 12 }}>
          Optimization Parameters
        </h3>
        <div style={{ display: 'flex', gap: 24, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div className="input-group" style={{ width: 280 }}>
            <label className="input-label">Target Agent</label>
            <select
              className="select-input"
              value={selectedAgentId}
              onChange={(e) => {
                setSelectedAgentId(e.target.value);
                setOptResult(null);
              }}
            >
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} (v{a.current_version})
                </option>
              ))}
            </select>
          </div>

          <div className="input-group">
            <label className="input-label">Optimization Focus Objectives</label>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {[
                ['accuracy', 'Grounding & Accuracy'],
                ['conciseness', 'Editorial Conciseness'],
                ['citations', 'Explicit Citations'],
                ['instructions', 'Constraint Enforcement'],
              ].map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  className={`chip ${focusAreas.includes(key) ? 'selected' : ''}`}
                  onClick={() => toggleFocus(key)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <button className="btn-primary" onClick={handleGenerate} disabled={optimizing || !selectedAgentId}>
            <Sparkles size={16} /> {optimizing ? 'Analyzing Prompt…' : 'Generate Optimization'}
          </button>
        </div>
      </div>

      {optResult && (
        <div className="card-elevated">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '2px solid var(--border-strong)', paddingBottom: 16, marginBottom: 20 }}>
            <div>
              <span className="page-head-eyebrow">ESTIMATED GAIN: +{optResult.score_delta}%</span>
              <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '22px', textTransform: 'uppercase' }}>
                Proposed Optimization Candidate
              </h3>
            </div>
            <button className="btn-primary" onClick={handleApprove} disabled={approving}>
              <Check size={16} /> {approving ? 'Applying & Bumping…' : 'Approve & Publish Revision'}
            </button>
          </div>

          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: 20 }}>
            {optResult.rationale}
          </p>

          <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '14px', textTransform: 'uppercase', marginBottom: 8 }}>
            Unified Diff View
          </h4>
          <pre className="diff-viewer">
            {optResult.diff_json?.diff_text || 'No diff lines recorded.'}
          </pre>
        </div>
      )}
    </>
  );
}

// ==============================================================================
// 9. DEPLOYMENTS & API KEYS VIEW
// ==============================================================================

function DeploymentsView({
  workspace,
  agents,
  showToast,
}: {
  workspace: Workspace;
  agents: Agent[];
  showToast: (m: string, t?: 'success' | 'error') => void;
}) {
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [showCreateDep, setShowCreateDep] = useState(false);
  const [showCreateKey, setShowCreateKey] = useState(false);
  const [depName, setDepName] = useState('');
  const [depAgentId, setDepAgentId] = useState(agents[0]?.id || '');
  const [depEnv, setDepEnv] = useState('production');
  const [keyName, setKeyName] = useState('');
  const [revealedKey, setRevealedKey] = useState<string | null>(null);
  const [previewDeployment, setPreviewDeployment] = useState<Deployment | null>(null);

  useEffect(() => {
    loadDeployments();
    loadApiKeys();
  }, [workspace]);

  const loadDeployments = async () => {
    try {
      const data = await api(`/workspaces/${workspace.id}/deployments`);
      setDeployments(data);
      if (data.length && !previewDeployment) setPreviewDeployment(data[0]);
    } catch (e: any) {}
  };

  const loadApiKeys = async () => {
    try {
      const data = await api(`/workspaces/${workspace.id}/api-keys`);
      setApiKeys(data);
    } catch (e: any) {}
  };

  const handleCreateDeployment = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api(`/workspaces/${workspace.id}/deployments`, {
        method: 'POST',
        body: JSON.stringify({ name: depName, agent_id: depAgentId, environment: depEnv }),
      });
      setShowCreateDep(false);
      setDepName('');
      loadDeployments();
      showToast(`Created deployment "${res.name}"`);
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleCreateApiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api(`/workspaces/${workspace.id}/api-keys`, {
        method: 'POST',
        body: JSON.stringify({ name: keyName }),
      });
      setShowCreateKey(false);
      setKeyName('');
      setRevealedKey(res.raw_key);
      loadApiKeys();
      showToast('Generated secure API key');
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleRevokeKey = async (k: ApiKey) => {
    if (!confirm(`Revoke key ${k.name} (${k.prefix})?`)) return;
    try {
      await api(`/workspaces/${workspace.id}/api-keys/${k.id}`, { method: 'DELETE' });
      showToast('Revoked key');
      loadApiKeys();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-head-eyebrow">DISTRIBUTION & INTEGRATION // DEPLOYMENT CENTER</div>
          <h1 className="page-head-title">Deployments & Keys.</h1>
          <p className="page-head-sub">
            Expose published agents through authenticated HTTP REST APIs or embed them with the VoiceBox web chat widget.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button className="btn-secondary" onClick={() => setShowCreateKey(true)}>
            <Key size={16} /> Generate API Key
          </button>
          <button className="btn-primary" onClick={() => setShowCreateDep(true)}>
            <Plus size={16} /> New Deployment
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 24, marginBottom: 32 }}>
        {/* Active Deployments */}
        <div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', textTransform: 'uppercase', marginBottom: 16 }}>
            Live Deployments ({deployments.length})
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {deployments.map((d) => (
              <div
                key={d.id}
                className="card"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '16px 20px',
                  borderLeft: previewDeployment?.id === d.id ? '4px solid var(--secondary)' : undefined,
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <b style={{ fontSize: '15px', textTransform: 'uppercase' }}>{d.name}</b>
                    <span className="status-chip status-success">{d.environment}</span>
                    <span className="chip" style={{ fontSize: '10px', padding: '2px 8px' }}>
                      {d.total_requests} REQS
                    </span>
                  </div>
                  <small style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                    ENDPOINT: /api/v1/public/deployments/{d.id}/chat
                  </small>
                </div>
                <button className="btn-secondary btn-sm" onClick={() => setPreviewDeployment(d)}>
                  Inspect Widget
                </button>
              </div>
            ))}
          </div>

          {/* Active API Keys */}
          <div style={{ marginTop: 32 }}>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', textTransform: 'uppercase', marginBottom: 16 }}>
              Hashed API Keys ({apiKeys.length})
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {apiKeys.map((k) => (
                <div key={k.id} className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 18px' }}>
                  <div>
                    <b>{k.name}</b>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>
                      PREFIX: {k.prefix} // SCOPES: {k.scopes}
                    </div>
                  </div>
                  <button className="btn-destructive btn-sm" onClick={() => handleRevokeKey(k)}>
                    Revoke
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Live Embed Widget Preview */}
        <div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', textTransform: 'uppercase', marginBottom: 16 }}>
            Embeddable Chat Widget Preview
          </h2>
          {previewDeployment ? (
            <div className="card-elevated" style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ background: '#0A0A0A', color: '#FAFAFA', padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <b style={{ fontFamily: 'var(--font-display)', textTransform: 'uppercase', fontSize: '14px' }}>
                    {previewDeployment.widget_config?.title || previewDeployment.name}
                  </b>
                  <div style={{ fontSize: '11px', color: '#A3A3A3' }}>VOICEBOX LIVE WIDGET</div>
                </div>
                <div style={{ width: 10, height: 10, background: 'var(--secondary)' }} />
              </div>
              <div style={{ padding: 24, minHeight: 200, background: '#FAFAFA' }}>
                <div style={{ background: '#FFFFFF', border: '2px solid var(--border-strong)', padding: 14, maxWidth: '85%' }}>
                  <p style={{ fontSize: '13px' }}>
                    {previewDeployment.widget_config?.welcome_message || 'Welcome! How can I assist you today?'}
                  </p>
                </div>
              </div>
              <div style={{ padding: 12, borderTop: '2px solid var(--border-strong)', background: '#FFFFFF', display: 'flex', gap: 8 }}>
                <input className="input-text" placeholder="Type a message..." disabled style={{ height: 38 }} />
                <button className="btn-primary btn-sm" disabled>
                  Send
                </button>
              </div>

              <div style={{ padding: 16, borderTop: '1px solid var(--border-subtle)', background: 'var(--surface)' }}>
                <b style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  HTML EMBED SNIPPET
                </b>
                <pre style={{ fontSize: '11px', padding: 10, marginTop: 6 }}>
                  {`<script src="https://cdn.agenttrainer.com/widget.js"\n  data-deployment="${previewDeployment.id}"\n  data-theme="voicebox"></script>`}
                </pre>
              </div>
            </div>
          ) : (
            <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)' }}>
              Create or select a deployment to inspect its embed configuration.
            </div>
          )}
        </div>
      </div>

      {/* Reveal API Key Modal */}
      {revealedKey && (
        <div className="modal-overlay">
          <div className="modal-box">
            <div className="modal-header">
              <h3 style={{ color: 'var(--secondary)' }}>SECURE API KEY GENERATED</h3>
              <button className="btn-ghost btn-sm" onClick={() => setRevealedKey(null)}>
                <X size={18} />
              </button>
            </div>
            <div className="modal-body">
              <div className="pull-quote" style={{ margin: 0, fontSize: '14px' }}>
                Copy this key now. For security purposes, this secret is hashed and will never be presented again.
              </div>
              <pre style={{ wordBreak: 'break-all' }}>{revealedKey}</pre>
            </div>
            <div className="modal-footer">
              <button
                className="btn-primary"
                onClick={() => {
                  navigator.clipboard.writeText(revealedKey);
                  showToast('Copied API key to clipboard');
                }}
              >
                <Copy size={16} /> Copy to Clipboard
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Deployment Modal */}
      {showCreateDep && (
        <div className="modal-overlay">
          <div className="modal-box">
            <div className="modal-header">
              <h3>CREATE AGENT DEPLOYMENT</h3>
              <button className="btn-ghost btn-sm" onClick={() => setShowCreateDep(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCreateDeployment}>
              <div className="modal-body">
                <div className="input-group">
                  <label className="input-label">Deployment Title</label>
                  <input
                    className="input-text"
                    placeholder="E.g. Production Web Support"
                    value={depName}
                    onChange={(e) => setDepName(e.target.value)}
                    required
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Target Agent</label>
                  <select className="select-input" value={depAgentId} onChange={(e) => setDepAgentId(e.target.value)}>
                    {agents.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name} (v{a.current_version})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="input-group">
                  <label className="input-label">Environment</label>
                  <select className="select-input" value={depEnv} onChange={(e) => setDepEnv(e.target.value)}>
                    <option value="production">Production</option>
                    <option value="staging">Staging</option>
                  </select>
                </div>
              </div>
              <div className="modal-footer">
                <button className="btn-secondary" type="button" onClick={() => setShowCreateDep(false)}>
                  Cancel
                </button>
                <button className="btn-primary" type="submit">
                  Launch Deployment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create API Key Modal */}
      {showCreateKey && (
        <div className="modal-overlay">
          <div className="modal-box">
            <div className="modal-header">
              <h3>GENERATE API CREDENTIAL</h3>
              <button className="btn-ghost btn-sm" onClick={() => setShowCreateKey(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCreateApiKey}>
              <div className="modal-body">
                <div className="input-group">
                  <label className="input-label">Key Identifier / Name</label>
                  <input
                    className="input-text"
                    placeholder="E.g. Mobile Client Key"
                    value={keyName}
                    onChange={(e) => setKeyName(e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button className="btn-secondary" type="button" onClick={() => setShowCreateKey(false)}>
                  Cancel
                </button>
                <button className="btn-primary" type="submit">
                  Generate
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

// ==============================================================================
// 10. ANALYTICS & AUDIT LOGS VIEW
// ==============================================================================

function AnalyticsView({
  workspace,
  showToast,
}: {
  workspace: Workspace;
  showToast: (m: string, t?: 'success' | 'error') => void;
}) {
  const [metrics, setMetrics] = useState<any>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  useEffect(() => {
    loadData();
  }, [workspace]);

  const loadData = async () => {
    try {
      const [m, logs] = await Promise.all([
        api(`/workspaces/${workspace.id}/analytics`),
        api(`/workspaces/${workspace.id}/audit-logs`),
      ]);
      setMetrics(m);
      setAuditLogs(logs);
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-head-eyebrow">TELEMETRY & COMPLIANCE // AUDIT RECORD</div>
          <h1 className="page-head-title">Analytics & Audit.</h1>
          <p className="page-head-sub">
            Real usage telemetry, token consumption, latency trends, and a verifiable audit log of every workspace event.
          </p>
        </div>
      </div>

      {metrics && (
        <div className="stats-strip">
          <div className="stat-cell">
            <div className="stat-label">Conversations</div>
            <div className="stat-value">{metrics.total_conversations}</div>
            <div className="stat-sub">{metrics.total_messages} messages recorded</div>
          </div>
          <div className="stat-cell">
            <div className="stat-label">Total Tokens</div>
            <div className="stat-value">{metrics.total_tokens.toLocaleString()}</div>
            <div className="stat-sub">Across chat and evaluations</div>
          </div>
          <div className="stat-cell">
            <div className="stat-label">Average Latency</div>
            <div className="stat-value">{metrics.avg_latency_ms}ms</div>
            <div className="stat-sub">Model roundtrip execution</div>
          </div>
          <div className="stat-cell">
            <div className="stat-label">Estimated AI Cost</div>
            <div className="stat-value">${metrics.total_estimated_cost}</div>
            <div className="stat-sub">Based on provider token rates</div>
          </div>
        </div>
      )}

      {/* Audit Trail Table */}
      <div style={{ marginTop: 32 }}>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '20px', textTransform: 'uppercase', marginBottom: 16 }}>
          Immutable Workspace Audit Trail ({auditLogs.length} Events)
        </h2>
        <div style={{ border: '2px solid var(--border-strong)', background: '#FFFFFF' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '180px 160px 1fr 180px', padding: '12px 16px', background: 'var(--surface)', borderBottom: '2px solid var(--border-strong)', fontFamily: 'var(--font-display)', fontSize: '11px', textTransform: 'uppercase' }}>
            <span>ACTION</span>
            <span>RESOURCE</span>
            <span>DETAILS</span>
            <span>TIMESTAMP</span>
          </div>
          {auditLogs.map((log) => (
            <div
              key={log.id}
              style={{
                display: 'grid',
                gridTemplateColumns: '180px 160px 1fr 180px',
                padding: '12px 16px',
                borderBottom: '1px solid var(--border-subtle)',
                fontSize: '13px',
                alignItems: 'center',
              }}
            >
              <b style={{ textTransform: 'uppercase', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                {log.action}
              </b>
              <span style={{ color: 'var(--text-secondary)' }}>{log.resource_type}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>
                {JSON.stringify(log.details_json || {})}
              </span>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                {new Date(log.created_at).toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

// ==============================================================================
// 11. SETTINGS VIEW
// ==============================================================================

function SettingsView({
  user,
  workspace,
  showToast,
}: {
  user: User;
  workspace: Workspace;
  showToast: (m: string, t?: 'success' | 'error') => void;
}) {
  const [members, setMembers] = useState<any[]>([]);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('member');
  const [inviting, setInviting] = useState(false);

  useEffect(() => {
    loadMembers();
  }, [workspace]);

  const loadMembers = async () => {
    try {
      const data = await api(`/workspaces/${workspace.id}/members`);
      setMembers(data);
    } catch (e: any) {}
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviting(true);
    try {
      await api(`/workspaces/${workspace.id}/members`, {
        method: 'POST',
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      });
      setInviteEmail('');
      loadMembers();
      showToast(`Invited ${inviteEmail} to workspace`);
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setInviting(false);
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-head-eyebrow">GOVERNANCE & ACCESS // WORKSPACE SETTINGS</div>
          <h1 className="page-head-title">Settings & Members.</h1>
          <p className="page-head-sub">
            Manage workspace ownership, team member roles, and security policies.
          </p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* Workspace Info */}
        <div className="card">
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', textTransform: 'uppercase', marginBottom: 16 }}>
            Workspace Particulars
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="input-group">
              <label className="input-label">Workspace Identifier</label>
              <input className="input-text" value={workspace.id} readOnly />
            </div>
            <div className="input-group">
              <label className="input-label">Workspace Title</label>
              <input className="input-text" value={workspace.name} readOnly />
            </div>
            <div className="input-group">
              <label className="input-label">Current Owner</label>
              <input className="input-text" value={user.email} readOnly />
            </div>
          </div>
        </div>

        {/* Members Management */}
        <div className="card">
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', textTransform: 'uppercase', marginBottom: 16 }}>
            Invite Team Colleague
          </h3>
          <form onSubmit={handleInvite} style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 20 }}>
            <div className="input-group">
              <label className="input-label">Colleague Work Email</label>
              <input
                type="email"
                className="input-text"
                placeholder="colleague@publication.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                required
              />
            </div>
            <div className="input-group">
              <label className="input-label">Assigned Role</label>
              <select className="select-input" value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
                <option value="member">Member (Can edit and test agents)</option>
                <option value="admin">Admin (Can manage settings and keys)</option>
                <option value="viewer">Viewer (Read-only observation)</option>
              </select>
            </div>
            <button className="btn-primary" type="submit" disabled={inviting}>
              {inviting ? 'Inviting…' : 'Send Workspace Invite'}
            </button>
          </form>

          <div>
            <b style={{ fontSize: '12px', textTransform: 'uppercase' }}>Workspace Members ({members.length})</b>
            <div style={{ marginTop: 8 }}>
              {members.map((m) => (
                <div key={m.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)', fontSize: '13px' }}>
                  <span>{m.user?.email || m.user_id}</span>
                  <span className="status-chip status-neutral">{m.role}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// Mount React Root
createRoot(document.getElementById('root')!).render(<App />);
