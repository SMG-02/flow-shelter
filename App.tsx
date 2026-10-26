import { useEffect, useMemo, useState, type ReactNode } from 'react'

type Screen =
  | 'welcome' | 'register' | 'login' | 'profile' | 'health' | 'goal-setup' | 'summary'
  | 'overview' | 'cashflow' | 'transactions' | 'goals' | 'transaction-form'
  | 'goal-detail' | 'goal-form' | 'contribution' | 'settings' | 'notifications'
type Tx = { id: number; type: 'Income' | 'Expense'; description: string; amount: number; date: string; status: string; category: string }

const money = (value: number) => new Intl.NumberFormat('en-ZA', { style: 'currency', currency: 'ZAR', maximumFractionDigits: 0 }).format(value)

function Button({ children, onClick, secondary = false, type = 'button' }: { children: ReactNode; onClick?: () => void; secondary?: boolean; type?: 'button' | 'submit' }) {
  return <button type={type} onClick={onClick} className={secondary ? 'btn secondary' : 'btn'}>{children}</button>
}
function Field({ label, type = 'text', placeholder, defaultValue, required = false }: { label: string; type?: string; placeholder?: string; defaultValue?: string; required?: boolean }) {
  return <label className="field"><span>{label}{required && ' *'}</span><input type={type} placeholder={placeholder} defaultValue={defaultValue} required={required} /></label>
}
function SelectField({ label, children, defaultValue }: { label: string; children: ReactNode; defaultValue?: string }) {
  return <label className="field"><span>{label}</span><select defaultValue={defaultValue}>{children}</select></label>
}
function Card({ children, className = '', onClick }: { children: ReactNode; className?: string; onClick?: () => void }) {
  return <section className={`card ${onClick ? 'clickable' : ''} ${className}`} onClick={onClick}>{children}</section>
}
function Status({ children }: { children: ReactNode }) { return <span className="status">{children}</span> }
function Progress({ value }: { value: number }) { return <div className="progress"><i style={{ width: `${Math.min(value, 100)}%` }} /></div> }
function DocumentIcon() {
  return <svg className="button-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12m-4-4 4 4 4-4M5 19h14" /></svg>
}
function Step({ current, total = 5, label }: { current: number; total?: number; label: string }) {
  return <div className="step"><div><span>{label}</span><b>Step {current} of {total}</b></div><Progress value={(current / total) * 100} /></div>
}

const translations: Record<string, { title: string; intro: string; create: string; login: string; nav: string[] }> = {
  English: { title: 'Know what is safe to spend.', intro: 'Plan around irregular income, essential bills and savings goals — without the guesswork.', create: 'Create account', login: 'Log in', nav: ['Overview', 'Cash flow', 'Transactions', 'Goals'] },
  isiZulu: { title: 'Yazi ukuthi kuphephile ukusebenzisa malini.', intro: 'Hlela imali engenayo engahleliwe, izikweletu ezibalulekile kanye nezinhloso zokonga.', create: 'Vula i-akhawunti', login: 'Ngena', nav: ['Ukubuka konke', 'Ukuhamba kwemali', 'Imisebenzi', 'Izinhloso'] },
  Sesotho: { title: 'Tseba hore o ka sebedisa bokae ka polokeho.', intro: 'Rera lekeno le sa tsitsang, ditshenyehelo tsa bohlokwa le dipheo tsa ho boloka.', create: 'Theha akhaonto', login: 'Kena', nav: ['Kakaretso', 'Phallo ya tjhelete', 'Ditransekshene', 'Dipheo'] },
  isiXhosa: { title: 'Yazi ukuba kukhuselekile ukusebenzisa malini.', intro: 'Cwangcisa ingeniso engaqhelekanga, amatyala abalulekileyo kunye neenjongo zokonga.', create: 'Yenza i-akhawunti', login: 'Ngena', nav: ['Isishwankathelo', 'Ukuhamba kwemali', 'Iintengiselwano', 'Iinjongo'] },
}

export default function App() {
  const [screen, setScreen] = useState<Screen>('welcome')
  const [language, setLanguage] = useState(() => localStorage.getItem('fs-language') || 'English')
  const [healthStep, setHealthStep] = useState(1)
  const [planView, setPlanView] = useState<'next' | 'monthly'>('next')
  const [filter, setFilter] = useState('All')
  const [goalSaved, setGoalSaved] = useState(4500)
  const [editingTx, setEditingTx] = useState<Tx | null>(null)
  const [txs, setTxs] = useState<Tx[]>([
    { id: 1, type: 'Income', description: 'Mokoena Studio project', amount: 12000, date: '28 Jun 2025', status: 'Expected', category: 'Client payment' },
    { id: 2, type: 'Expense', description: 'Apartment rent', amount: 6500, date: '25 Jun 2025', status: 'Upcoming', category: 'Housing' },
    { id: 3, type: 'Expense', description: 'Fibre internet', amount: 799, date: '22 Jun 2025', status: 'Paid', category: 'Utilities' },
    { id: 4, type: 'Income', description: 'Website deposit', amount: 3500, date: '18 Jun 2025', status: 'Received', category: 'Client payment' },
    { id: 5, type: 'Expense', description: 'Groceries', amount: 1400, date: '26 Jun 2025', status: 'Upcoming', category: 'Food' },
  ])
  useEffect(() => { localStorage.setItem('fs-language', language) }, [language])
  const currentBalance = useMemo(() => 18450 + txs.filter(t => t.status === 'Received' && t.id !== 4).reduce((a, t) => a + t.amount, 0) - txs.filter(t => t.status === 'Paid' && t.id !== 3).reduce((a, t) => a + t.amount, 0), [txs])
  const upcoming = txs.filter(t => t.type === 'Expense' && t.status !== 'Paid').reduce((a, t) => a + t.amount, 0)
  const expected = txs.filter(t => t.type === 'Income' && t.status !== 'Received').reduce((a, t) => a + t.amount, 0)
  const projected = currentBalance - upcoming + expected
  const t = translations[language]

  const markDone = (tx: Tx) => setTxs(items => items.map(item => item.id === tx.id ? { ...item, status: tx.type === 'Income' ? 'Received' : 'Paid' } : item))

  if (screen === 'welcome') return <main className="welcome">
    <div className="brand">FS <span>FlowShelter</span></div>
    <div className="welcome-copy">
      <p className="eyebrow">MONEY PLANNING FOR FREELANCERS</p><h1>{t.title}</h1><p>{t.intro}</p>
      <label className="language"><span>Language</span><select value={language} onChange={e => setLanguage(e.target.value)}>{Object.keys(translations).map(l => <option key={l}>{l}</option>)}</select></label>
      <div className="actions"><Button onClick={() => setScreen('register')}>{t.create}</Button><Button secondary onClick={() => setScreen('login')}>{t.login}</Button></div>
      <small>Your language preference is saved on this device.</small>
    </div>
    <aside className="wire-preview"><span>Illustrative preview</span><div className="preview-card"><small>Available now</small><b>R18 450</b><i /></div><div className="preview-lines"><i/><i/><i/></div></aside>
  </main>

  if (screen === 'register' || screen === 'login') return <Auth screen={screen} go={setScreen} />
  if (screen === 'profile') return <OnboardingShell step={1} title="Tell us about your work">
    <p className="muted">This helps us shape a useful first cash-flow plan. No client details needed.</p>
    <div className="form-grid"><Field label="Type of freelance work" placeholder="e.g. Graphic designer" required /><SelectField label="Income pattern" defaultValue="Irregular"><option>Weekly</option><option>Fortnightly</option><option>Monthly</option><option>Irregular</option><option>Unsure</option></SelectField><Field label="Typical income amount (optional)" type="number" placeholder="R 0" /><Field label="Next expected payment date (optional)" type="date" /><Field label="Next expected payment amount (optional)" type="number" placeholder="R 0" /><SelectField label="Currency" defaultValue="ZAR"><option>ZAR — South African rand</option></SelectField></div>
    <div className="footer-actions"><button className="text-btn">Skip optional details</button><Button onClick={() => setScreen('health')}>Continue</Button></div>
  </OnboardingShell>
  if (screen === 'health') return <Health step={healthStep} setStep={setHealthStep} done={() => setScreen('goal-setup')} />
  if (screen === 'goal-setup') return <OnboardingShell step={4} title="Set your first savings goal">
    <p className="muted">Optional. You can create or change goals at any time.</p>
    <div className="form-grid"><Field label="Goal name" defaultValue="Emergency buffer" required /><Field label="Target amount" defaultValue="30000" type="number" required /><Field label="Already saved" defaultValue="4500" type="number" /><Field label="Target date (optional)" type="date" /><SelectField label="Priority (optional)"><option>Medium</option><option>High</option><option>Low</option></SelectField></div>
    <div className="footer-actions"><Button secondary onClick={() => setScreen('summary')}>Skip for now</Button><Button onClick={() => setScreen('summary')}>Create goal</Button></div>
  </OnboardingShell>
  if (screen === 'summary') return <OnboardingShell step={5} title="Your starting picture">
    <p className="sample">ILLUSTRATIVE SUMMARY · based on the details you entered</p>
    <div className="summary-grid"><Card><small>Available now</small><h2>{money(currentBalance)}</h2><p>Money recorded as currently available</p></Card><Card><small>Projected after known events</small><h2>{money(projected)}</h2><p>Includes expected income of {money(expected)} — not yet received</p></Card></div>
    <Card><h3>Before your next expected payment</h3><div className="row"><span>Essential commitments</span><b>{money(upcoming)}</b></div><div className="row"><span>Next income · Expected · 28 Jun</span><b>+{money(12000)}</b></div></Card>
    <div className="notice">Some dates are missing. This forecast is an estimate and may change.</div>
    <div className="footer-actions"><Button secondary onClick={() => setScreen('health')}>Edit details</Button><Button onClick={() => setScreen('overview')}>Go to dashboard</Button></div>
  </OnboardingShell>

  return <AppShell screen={screen} setScreen={setScreen} nav={t.nav}>
    {screen === 'overview' && <Dashboard balance={currentBalance} projected={projected} txs={txs} goalSaved={goalSaved} go={setScreen} />}
    {screen === 'transactions' && <Transactions txs={txs} filter={filter} setFilter={setFilter} go={setScreen} edit={tx => { setEditingTx(tx); setScreen('transaction-form') }} markDone={markDone} />}
    {screen === 'transaction-form' && <TransactionForm tx={editingTx} cancel={() => { setEditingTx(null); setScreen('transactions') }} save={(tx) => { setTxs(old => editingTx ? old.map(x => x.id === editingTx.id ? tx : x) : [...old, { ...tx, id: Date.now() }]); setEditingTx(null); setScreen('transactions') }} />}
    {screen === 'cashflow' && <CashFlow view={planView} setView={setPlanView} balance={currentBalance} projected={projected} go={setScreen} />}
    {screen === 'goals' && <Goals saved={goalSaved} go={setScreen} />}
    {screen === 'goal-detail' && <GoalDetail saved={goalSaved} go={setScreen} />}
    {screen === 'goal-form' && <GoalForm go={setScreen} />}
    {screen === 'contribution' && <Contribution go={setScreen} add={(n) => setGoalSaved(v => v + n)} />}
    {screen === 'settings' && <Settings language={language} setLanguage={setLanguage} />}
    {screen === 'notifications' && <Notifications go={setScreen} />}
  </AppShell>
}

function Auth({ screen, go }: { screen: 'register' | 'login'; go: (s: Screen) => void }) {
  const register = screen === 'register'
  const [show, setShow] = useState(false)
  return <main className="auth"><button className="back" onClick={() => go('welcome')}>← Back</button><div className="auth-card"><div className="brand">FS <span>FlowShelter</span></div><p className="eyebrow">{register ? 'GET STARTED' : 'WELCOME BACK'}</p><h1>{register ? 'Create your account' : 'Log in'}</h1><Field label="Email address" type="email" placeholder="you@example.co.za" required /><label className="field"><span>Password *</span><div className="password"><input type={show ? 'text' : 'password'} placeholder="Enter your password" /><button onClick={() => setShow(!show)}>{show ? 'Hide' : 'Show'}</button></div></label>{register ? <><p className="hint">Use 8+ characters with a number and symbol.</p><label className="check"><input type="checkbox" /> I accept the Terms and Privacy Notice.</label></> : <button className="text-btn right">Forgot password?</button>}<Button onClick={() => go(register ? 'profile' : 'overview')}>{register ? 'Create account' : 'Log in'}</Button><p className="center">{register ? 'Already have an account?' : 'New to FlowShelter?'} <button className="link" onClick={() => go(register ? 'login' : 'register')}>{register ? 'Log in' : 'Create account'}</button></p></div></main>
}

function OnboardingShell({ step, title, children }: { step: number; title: string; children: ReactNode }) {
  return <main className="onboarding"><header><div className="brand">FS <span>FlowShelter</span></div><button className="text-btn">Save & exit</button></header><div className="onboarding-card"><Step current={step} label="Set up your plan" /><h1>{title}</h1>{children}</div></main>
}

function Health({ step, setStep, done }: { step: number; setStep: (n: number) => void; done: () => void }) {
  const content = [
    <><h1>What do you have available now?</h1><p className="muted">Only include money you can currently use. Do not include expected payments.</p><Field label="Current available balance" type="number" defaultValue="18450" required /><Field label="Existing savings (optional)" type="number" placeholder="R 0" /></>,
    <><h1>What income are you expecting?</h1><p className="muted">Expected money is kept separate until you mark it received.</p><Card><div className="row"><b>Mokoena Studio project</b><Status>Expected</Status></div><div className="form-grid"><Field label="Amount" defaultValue="12000" /><Field label="Expected date" type="date" defaultValue="2025-06-28" /></div><button className="text-btn">Remove</button></Card><Button secondary>+ Add another income</Button></>,
    <><h1>What must you pay?</h1><p className="muted">Add essential expenses and upcoming commitments.</p><Card><Field label="Expense" defaultValue="Apartment rent" /><div className="form-grid"><Field label="Amount" defaultValue="6500" /><Field label="Due date" type="date" defaultValue="2025-06-25" /></div><button className="text-btn">Remove</button></Card><Button secondary>+ Add another expense</Button></>,
  ][step - 1]
  return <OnboardingShell step={step + 1} title=""><div className="health">{content}<div className="notice">You can use “Not sure” where details are unknown. Your forecast will be labelled as an estimate.</div><div className="footer-actions"><Button secondary onClick={() => step > 1 && setStep(step - 1)}>Back</Button><Button onClick={() => step === 3 ? done() : setStep(step + 1)}>{step === 3 ? 'Review & continue' : 'Continue'}</Button></div></div></OnboardingShell>
}

function AppShell({ screen, setScreen, nav, children }: { screen: Screen; setScreen: (s: Screen) => void; nav: string[]; children: ReactNode }) {
  const routes: Screen[] = ['overview', 'cashflow', 'transactions', 'goals']
  return <div className="app-shell"><aside className="sidebar"><div className="brand">FS <span>FlowShelter</span></div><nav>{routes.map((r, i) => <button key={r} className={screen === r ? 'active' : ''} onClick={() => setScreen(r)}><i>{['⌂', '↗', '↕', '◇'][i]}</i>{nav[i]}</button>)}</nav><div className="side-note"><small>Illustrative data</small><p>Records shown here are for prototype review.</p></div></aside><div className="app-main"><header className="app-header"><div><p className="eyebrow">FLOWSHELTER</p><b>{screen.replace('-', ' ')}</b></div><div><button aria-label="Notifications" onClick={() => setScreen('notifications')}>○<span className="dot" /></button><button className="avatar" onClick={() => setScreen('settings')}>TM</button></div></header><main className="content">{children}</main></div><nav className="bottom-nav">{routes.map((r, i) => <button key={r} className={screen === r ? 'active' : ''} onClick={() => setScreen(r)}><i>{['⌂', '↗', '↕', '◇'][i]}</i><span>{nav[i]}</span></button>)}</nav></div>
}

function Dashboard({ balance, projected, txs, goalSaved, go }: { balance: number; projected: number; txs: Tx[]; goalSaved: number; go: (s: Screen) => void }) {
  const [exportOpen, setExportOpen] = useState(false)
  const [preparing, setPreparing] = useState(false)
  const received = txs.filter(t => t.type === 'Income' && t.status === 'Received').reduce((sum, t) => sum + t.amount, 0)
  const expected = txs.filter(t => t.type === 'Income' && t.status !== 'Received').reduce((sum, t) => sum + t.amount, 0)
  const upcomingTxs = txs.filter(t => t.type === 'Expense' && t.status !== 'Paid')
  const upcoming = upcomingTxs.reduce((sum, t) => sum + t.amount, 0)
  const openExport = () => {
    setPreparing(true)
    window.setTimeout(() => {
      setPreparing(false)
      setExportOpen(true)
    }, 350)
  }
  return <><div className="page-title"><div><p className="eyebrow">ILLUSTRATIVE DATA</p><h1>Good morning, Thandi</h1><p>Here is what needs your attention before 28 June.</p></div><div className="actions"><Button onClick={() => go('transaction-form')}>+ Add transaction</Button><Button onClick={openExport}><DocumentIcon />{preparing ? 'Preparing…' : 'Export Summary'}</Button></div></div><div className="notice warning"><b>Payment due in 4 days.</b> Mokoena Studio payment is still expected. <button onClick={() => go('transactions')}>Review</button></div><div className="balance-grid"><Card><small>AVAILABLE NOW</small><h2>{money(balance)}</h2><p>Confirmed money you can use today</p></Card><Card><small>PROJECTED AFTER PLANNED EVENTS</small><h2>{money(projected)}</h2><p>Estimate if expected income arrives</p></Card><Card className="dark"><small>NEXT EXPECTED PAYMENT</small><h2>{money(12000)}</h2><div className="row"><span>28 June · 4 days</span><Status>Expected</Status></div></Card></div><div className="quick"><Button onClick={() => go('transaction-form')}>+ Add income</Button><Button secondary onClick={() => go('transaction-form')}>− Add expense</Button><Button secondary onClick={() => go('cashflow')}>View cash-flow plan →</Button></div><div className="dashboard-grid"><Card className="span-2" onClick={() => go('cashflow')}><div className="section-head"><div><p className="eyebrow">UNTIL NEXT PAYMENT</p><h3>Cash-flow outlook</h3></div><b>{money(projected)}</b></div><div className="mini-chart"><i /><i /><i /><i /></div><p className="muted">Lowest estimated balance: {money(9751)} on 26 June</p></Card><Card onClick={() => go('goal-detail')}><p className="eyebrow">SAVINGS GOAL</p><h3>Emergency buffer</h3><Progress value={(goalSaved / 30000) * 100} /><div className="row"><b>{money(goalSaved)}</b><span>of {money(30000)}</span></div></Card><Card><div className="section-head"><h3>Upcoming bills</h3><button onClick={() => go('transactions')}>See all</button></div>{upcomingTxs.map(t => <div className="list-row" key={t.id}><div><b>{t.description}</b><small>{t.date} · {t.status}</small></div><b>−{money(t.amount)}</b></div>)}</Card><Card className="span-2"><div className="section-head"><h3>Recent activity</h3><button onClick={() => go('transactions')}>See all</button></div>{txs.slice(2, 5).map(t => <div className="list-row" key={t.id}><div><b>{t.description}</b><small>{t.date} · {t.status}</small></div><b>{t.type === 'Income' ? '+' : '−'}{money(t.amount)}</b></div>)}</Card></div>{exportOpen && <SummaryExport balance={balance} projected={projected} received={received} expected={expected} upcoming={upcoming} upcomingTxs={upcomingTxs} goalSaved={goalSaved} close={() => setExportOpen(false)} />}</>
}

function SummaryExport({ balance, projected, received, expected, upcoming, upcomingTxs, goalSaved, close }: { balance: number; projected: number; received: number; expected: number; upcoming: number; upcomingTxs: Tx[]; goalSaved: number; close: () => void }) {
  return <div className="export-overlay" role="presentation" onMouseDown={e => e.target === e.currentTarget && close()}><section className="export-dialog" role="dialog" aria-modal="true" aria-labelledby="export-title"><div className="export-controls"><div><p className="eyebrow">SUMMARY PREVIEW</p><h2 id="export-title">Export financial summary</h2><p>Review the demo information before saving or sharing.</p></div><button className="close-button" aria-label="Close export preview" onClick={close}>×</button></div><article className="export-sheet"><header><div className="brand">FS <span>FlowShelter</span></div><div><b>Financial summary</b><small>Illustrative demo data · 24 June 2025</small></div></header><div className="export-overview"><div><small>AVAILABLE NOW</small><h2>{money(balance)}</h2><p>Confirmed current funds</p></div><div><small>PROJECTED BALANCE</small><h2>{money(projected)}</h2><p>If expected income arrives</p></div></div><section><h3>Income</h3><div className="export-row"><span>Received income</span><b>{money(received)}</b></div><div className="export-row"><span>Expected, not yet received</span><b>{money(expected)}</b></div></section><section><h3>Upcoming commitments</h3>{upcomingTxs.map(tx => <div className="export-row" key={tx.id}><span>{tx.description}<small>{tx.date} · {tx.status}</small></span><b>{money(tx.amount)}</b></div>)}<div className="export-total"><span>Total upcoming</span><b>{money(upcoming)}</b></div></section><section><h3>Savings</h3><div className="export-row"><span>Emergency buffer<small>{Math.round((goalSaved / 30000) * 100)}% of {money(30000)} goal</small></span><b>{money(goalSaved)}</b></div><Progress value={(goalSaved / 30000) * 100} /></section><section><h3>Cash-flow outlook</h3><p>Starting with {money(balance)}, known upcoming commitments total {money(upcoming)}. The projected balance is {money(projected)} if {money(expected)} in expected income arrives.</p><div className="notice">Expected income is not guaranteed and remains separate from money received.</div></section><footer>No financial health score is shown because this prototype does not calculate one.</footer></article><div className="export-actions"><p>Select “Save as PDF” in your browser’s print dialog to create a PDF file.</p><div className="actions"><Button secondary onClick={close}>Cancel</Button><Button onClick={() => window.print()}><DocumentIcon />Print / Save as PDF</Button></div></div></section></div>
}

function Transactions({ txs, filter, setFilter, go, edit, markDone }: { txs: Tx[]; filter: string; setFilter: (s: string) => void; go: (s: Screen) => void; edit: (t: Tx) => void; markDone: (t: Tx) => void }) {
  const shown = txs.filter(t => filter === 'All' || t.type === filter.slice(0, -1))
  return <><div className="page-title"><div><h1>Transactions</h1><p>Expected income stays separate until it is received.</p></div><Button onClick={() => go('transaction-form')}>+ Add transaction</Button></div><div className="toolbar"><div className="tabs">{['All', 'Income', 'Expenses'].map(x => <button className={filter === x ? 'active' : ''} onClick={() => setFilter(x)} key={x}>{x}</button>)}</div><Field label="From date (optional)" type="date" /></div><Card><p className="eyebrow">JUNE 2025</p>{shown.map(tx => <div className="transaction" key={tx.id} onClick={() => edit(tx)}><div className="type-mark">{tx.type === 'Income' ? '+' : '−'}</div><div><b>{tx.description}</b><small>{tx.date} · {tx.category}</small></div><div className="tx-amount"><b>{tx.type === 'Income' ? '+' : '−'}{money(tx.amount)}</b><Status>{tx.status}</Status></div>{!['Received', 'Paid'].includes(tx.status) && <button onClick={e => { e.stopPropagation(); markDone(tx) }}>Mark {tx.type === 'Income' ? 'received' : 'paid'}</button>}</div>)}</Card></>
}

function TransactionForm({ tx, cancel, save }: { tx: Tx | null; cancel: () => void; save: (t: Tx) => void }) {
  const [type, setType] = useState<'Income' | 'Expense'>(tx?.type || 'Income')
  return <><div className="page-title"><div><h1>{tx ? 'Edit transaction' : 'Add transaction'}</h1><p>Record expected and completed payments clearly.</p></div></div><Card className="form-card"><div className="tabs"><button className={type === 'Income' ? 'active' : ''} onClick={() => setType('Income')}>Income</button><button className={type === 'Expense' ? 'active' : ''} onClick={() => setType('Expense')}>Expense</button></div><Field label="Description" defaultValue={tx?.description} placeholder="e.g. Project payment" required /><div className="form-grid"><Field label="Amount (ZAR)" type="number" defaultValue={String(tx?.amount || '')} required /><Field label="Date" type="date" /></div><div className="form-grid"><SelectField label="Status"><option>{type === 'Income' ? 'Expected' : 'Upcoming'}</option><option>{type === 'Income' ? 'Received' : 'Paid'}</option><option>Overdue</option></SelectField><SelectField label="Category"><option>Client payment</option><option>Housing</option><option>Utilities</option><option>Food</option></SelectField></div><SelectField label="Recurrence (optional)"><option>Does not repeat</option><option>Weekly</option><option>Monthly</option></SelectField><label className="field"><span>Notes (optional)</span><textarea placeholder="Add context" /></label><div className="footer-actions"><Button secondary onClick={cancel}>Cancel</Button><Button onClick={() => save({ id: tx?.id || 0, type, description: tx?.description || 'New project payment', amount: tx?.amount || 5000, date: tx?.date || '30 Jun 2025', status: type === 'Income' ? 'Expected' : 'Upcoming', category: tx?.category || 'Client payment' })}>Save transaction</Button></div></Card></>
}

function CashFlow({ view, setView, balance, projected, go }: { view: string; setView: (v: 'next' | 'monthly') => void; balance: number; projected: number; go: (s: Screen) => void }) {
  const monthly = view === 'monthly'
  const events = monthly ? [['1 Jun', 'Starting balance', balance], ['18 Jun', 'Website deposit · Received', 21950], ['22 Jun', 'Fibre · Paid', 21151], ['25 Jun', 'Rent · Upcoming', 14651], ['28 Jun', 'Studio project · Expected', 26651], ['30 Jun', 'Planned savings allocation', 25651]] : [['Today', 'Available now', balance], ['25 Jun', 'Apartment rent · Upcoming', 11950], ['26 Jun', 'Groceries · Upcoming', 10550], ['28 Jun', 'Studio project · Expected', 22550]]
  return <><div className="page-title"><div><h1>Cash-flow plan</h1><p>A chronological estimate — expected money is not guaranteed.</p></div><Button onClick={() => go('transaction-form')}>+ Add event</Button></div><div className="tabs large"><button className={!monthly ? 'active' : ''} onClick={() => setView('next')}>Until next payment</button><button className={monthly ? 'active' : ''} onClick={() => setView('monthly')}>Monthly</button></div><div className="plan-grid"><Card><div className="section-head"><div><p className="eyebrow">SELECTED PERIOD</p><h3>{monthly ? 'June 2025' : 'Today – 28 June 2025'}</h3></div>{monthly && <div><button>←</button> <button>→</button></div>}</div><div className="timeline">{events.map((e, i) => <button key={String(e[0])} className="event" onClick={() => i > 0 && go('transactions')}><span>{e[0]}</span><i /><div><b>{e[1]}</b>{String(e[1]).includes('Expected') && <small>Depends on payment arriving</small>}</div><strong>{money(Number(e[2]))}</strong></button>)}</div></Card><aside><Card><small>STARTING BALANCE</small><h2>{money(balance)}</h2></Card><Card><small>PROJECTED END BALANCE</small><h2>{money(monthly ? projected - 1000 : projected)}</h2><p>Includes {money(12000)} expected, not received.</p></Card><div className="notice">Planned savings: {monthly ? money(1000) : money(0)}. This is not an automatic transfer.</div></aside></div></>
}

function Goals({ saved, go }: { saved: number; go: (s: Screen) => void }) {
  return <><div className="page-title"><div><h1>Savings goals</h1><p>Track contributions manually. FlowShelter does not move money.</p></div><Button onClick={() => go('goal-form')}>+ Add goal</Button></div><Card className="goal-card" onClick={() => go('goal-detail')}><div className="section-head"><div><p className="eyebrow">ACTIVE GOAL</p><h2>Emergency buffer</h2></div><Status>On track</Status></div><Progress value={(saved / 30000) * 100} /><div className="three-stats"><div><small>SAVED</small><b>{money(saved)}</b></div><div><small>REMAINING</small><b>{money(30000 - saved)}</b></div><div><small>TARGET</small><b>{money(30000)}</b></div></div><p>Target date: 31 December 2025</p></Card><Card className="empty"><h3>Planning another goal?</h3><p>Create a goal for tax, equipment or time off.</p><Button secondary onClick={() => go('goal-form')}>Create another goal</Button></Card></>
}
function GoalDetail({ saved, go }: { saved: number; go: (s: Screen) => void }) {
  return <><button className="back" onClick={() => go('goals')}>← All goals</button><div className="page-title"><div><p className="eyebrow">SAVINGS GOAL</p><h1>Emergency buffer</h1><p>Target date · 31 December 2025</p></div><div className="actions"><Button secondary onClick={() => go('goal-form')}>Edit goal</Button><Button onClick={() => go('contribution')}>+ Add contribution</Button></div></div><Card><Progress value={(saved / 30000) * 100} /><div className="three-stats"><div><small>SAVED</small><h2>{money(saved)}</h2></div><div><small>REMAINING</small><h2>{money(30000 - saved)}</h2></div><div><small>TARGET</small><h2>{money(30000)}</h2></div></div></Card><Card><h3>Contribution history</h3><div className="list-row"><div><b>Manual contribution</b><small>12 June 2025 · Monthly set-aside</small></div><b>+{money(1500)}</b></div><div className="list-row"><div><b>Opening amount</b><small>1 May 2025</small></div><b>+{money(3000)}</b></div></Card><p className="muted">Contributions are records only. No funds are transferred by FlowShelter.</p></>
}
function GoalForm({ go }: { go: (s: Screen) => void }) { return <><div className="page-title"><h1>Create or edit goal</h1></div><Card className="form-card"><Field label="Goal name" placeholder="e.g. Tax reserve" /><div className="form-grid"><Field label="Target amount" type="number" /><Field label="Current saved amount" type="number" /></div><Field label="Target date (optional)" type="date" /><div className="footer-actions"><Button secondary onClick={() => go('goals')}>Cancel</Button><Button onClick={() => go('goals')}>Save goal</Button></div></Card></> }
function Contribution({ go, add }: { go: (s: Screen) => void; add: (n: number) => void }) { const [amount, setAmount] = useState(1000); return <><div className="page-title"><div><h1>Add contribution</h1><p>Emergency buffer</p></div></div><Card className="form-card"><label className="field"><span>Amount (ZAR)</span><input type="number" value={amount} onChange={e => setAmount(Number(e.target.value))} /></label><Field label="Date" type="date" defaultValue="2025-06-24" /><Field label="Note (optional)" placeholder="e.g. June set-aside" /><div className="notice">This records progress only. It does not transfer money.</div><div className="footer-actions"><Button secondary onClick={() => go('goal-detail')}>Cancel</Button><Button onClick={() => { add(amount); go('goal-detail') }}>Record contribution</Button></div></Card></> }
function Settings({ language, setLanguage }: { language: string; setLanguage: (s: string) => void }) { return <><div className="page-title"><h1>Profile & settings</h1></div><Card className="form-card"><h3>Preferences</h3><SelectField label="Language" defaultValue={language}>{Object.keys(translations).map(x => <option key={x}>{x}</option>)}</SelectField><SelectField label="Currency" defaultValue="ZAR"><option>ZAR — South African rand</option></SelectField><Button onClick={() => setLanguage((document.querySelector('select') as HTMLSelectElement)?.value || language)}>Save preferences</Button><hr /><h3>Account</h3><button className="text-btn">Security and privacy</button><button className="text-btn">Log out</button></Card></> }
function Notifications({ go }: { go: (s: Screen) => void }) { return <><div className="page-title"><h1>Notifications</h1></div><Card><div className="list-row"><div><b>Expected payment due soon</b><small>Mokoena Studio payment is due in 4 days.</small></div><Status>New</Status></div><div className="list-row"><div><b>Rent is upcoming</b><small>{money(6500)} is due on 25 June.</small></div></div><button className="text-btn" onClick={() => go('cashflow')}>Review cash-flow plan →</button></Card></> }
