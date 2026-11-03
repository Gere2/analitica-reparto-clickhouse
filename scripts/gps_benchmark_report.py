"""English evidence summary and optional Matplotlib charts from a GPS report."""
import argparse
import json
import statistics
from pathlib import Path


def phase_rows(report):
    output=[]
    for phase in report['phases']:
        logs=[s['server'] for s in phase['samples'] if s['ok'] and s.get('server')]
        output.append(dict(design=phase['design'],concurrency=phase['concurrency'],
            repetition=phase['repetition'],**phase['summary'],
            median_server_ms=statistics.median(float(r['query_duration_ms']) for r in logs) if logs else None,
            median_read_rows=statistics.median(int(r['read_rows']) for r in logs) if logs else None,
            median_read_bytes=statistics.median(int(r['read_bytes']) for r in logs) if logs else None,
            peak_query_memory_mib=max((int(r['memory_usage']) for r in logs),default=0)/1048576 if logs else None))
    return output


def conclusion(report, rows):
    if not report.get('valid_comparison') or report['status']!='complete':
        return 'No capacity conclusion: the experiment stopped or the comparison was invalid. Inspect the stop reason and original samples.'
    if report['purpose']=='smoke':
        return 'Smoke validation only. This run is not a capacity measurement.'
    if not report.get('query_log_coverage',{}).get('complete'):
        return 'Client timings are available, but server evidence is incomplete. Resolve query-log coverage before attributing a bottleneck.'
    expected=report['parameters']['repetitions']
    candidates=[]
    for c in sorted({r['concurrency'] for r in rows}):
        a=[r for r in rows if r['design']=='history' and r['concurrency']==c]
        b=[r for r in rows if r['design']=='prepared' and r['concurrency']==c]
        if (len(a)==len(b)==expected and all(r['complete'] and r['slo_status']=='fail' for r in a)
                and all(r['complete'] and r['slo_status']=='pass' for r in b)):
            candidates.append(c)
    if candidates:
        prefix='Exploratory candidate' if report['purpose']=='exploration' else 'Observed repeated workload'
        return f'{prefix}: at concurrency {candidates[0]}, history missed the experimental SLO in every repetition and prepared state met it. This describes the tested machine, query and settings; inspect server counters to explain the cause.'
    if rows and all(r['slo_status']=='pass' for r in rows):
        return 'The experimental latency boundary was not reached within the tested range.'
    return 'The measured phases do not establish a consistent history-fails / prepared-passes boundary. Inspect both curves and repeat near the candidate threshold.'


def render(path, plot=False):
    report=json.loads(path.read_text(encoding='utf-8'))
    if report.get('schema_version')!=1:
        raise ValueError('Unsupported GPS report schema.')
    rows=phase_rows(report)
    parameters=report['parameters']
    lines=['# GPS history and prepared latest state','',
        f"Status: **{report['status']}**. Purpose: **{report['purpose']}**.",
        f"Environment: {report['label']}",
        f"Started UTC: {report['started_at_utc']}",
        f"GPS run: `{parameters['run_id']}`. Expected rows: {parameters['expected_rows']:,}; couriers: {parameters['expected_couriers']}.",
        f"Experimental client p95 target: {parameters['slo_ms']:g} ms, with zero failed requests.",
        '',conclusion(report,rows),'',
        'Client time includes Python and local HTTP. Percentiles use successful requests; failures are counted separately. Warmups are excluded. Query-result cache is off; OS cache remains uncontrolled.',
        'This is a closed-loop fixed-concurrency test. Low prepared-query latency can expose client overhead; QPS is not automatically a database maximum.',
        '', '| Design | Readers | Repeat | N | Errors | p50 client ms | p95 client ms | Median server ms | Median rows read | Peak query MiB | SLO |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    def fmt(v):
        return 'n/a' if v is None else f'{v:,.2f}'
    for r in rows:
        lines.append(f"| {r['design']} | {r['concurrency']} | {r['repetition']} | {r['attempted']} | {r['errors']} | {fmt(r['p50_client_ms'])} | {fmt(r['p95_client_ms'])} | {fmt(r['median_server_ms'])} | {fmt(r['median_read_rows'])} | {fmt(r['peak_query_memory_mib'])} | {r['slo_status']} |")
    if report.get('stop_reason'):
        lines.extend(['', 'Stop reason: '+report['stop_reason']])
    lines.extend(['','## Evidence','',
        'report.json contains settings, table definitions, snapshots, SQL, per-request results and query-log coverage. reference-output.json contains the frozen position answer. phases.csv and samples.csv contain the measured values.',
        'Peak query memory is not container RAM. Physical source rows and partial aggregate-state rows have different meanings. The two SELECT designs do not measure the insertion/storage cost of maintaining materialized views.',
        'Use only actual measured data in the presentation. Validate result equality and repeat the same workload before claiming an improvement.'])
    target=path.parent/'summary.md'
    target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    if plot:
        make_plot(path.parent,report,rows)
    return target


def make_plot(folder, report, rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for design,color in [('history','#9b512b'),('prepared','#187251')]:
        selected=[r for r in rows if r['design']==design and r['complete']]
        xs=sorted({r['concurrency'] for r in selected})
        ys=[statistics.median(r['p95_client_ms'] for r in selected if r['concurrency']==c) for c in xs]
        axes[0].plot(xs,ys,'o-',color=color,label=design)
        reads=[statistics.median(r['median_read_rows'] for r in selected if r['concurrency']==c and r['median_read_rows'] is not None)
               if any(r['concurrency']==c and r['median_read_rows'] is not None for r in selected) else float('nan') for c in xs]
        axes[1].plot(xs,reads,'o-',color=color,label=design)
    axes[0].axhline(report['parameters']['slo_ms'],color='#777',linestyle='--',label='Experimental target')
    axes[0].set_ylabel('Client p95 (ms), median across repetitions')
    axes[1].set_ylabel('Rows read, median across phases')
    for ax in axes:
        ax.set_xlabel('Concurrent readers');ax.grid(alpha=.2);ax.legend();ax.set_ylim(bottom=0)
        ax.set_xticks(sorted({r['concurrency'] for r in rows}))
        ax.spines[['top','right']].set_visible(False)
    warning=(' — INCOMPLETE' if not report.get('valid_comparison') else
             ' — SMOKE VALIDATION' if report['purpose']=='smoke' else '')
    fig.suptitle('GPS history vs prepared latest state'+warning,fontsize=14)
    fig.text(.05,.025,f"{report['parameters']['expected_rows']:,} GPS rows · {report['parameters']['expected_couriers']} couriers · {report['purpose']} · warm, closed-loop test",fontsize=9)
    fig.tight_layout(rect=(0,.07,1,.93))
    fig.savefig(folder/'comparison.png',dpi=180)
    fig.savefig(folder/'comparison.svg')
    plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('--plot',action='store_true',help='Optional Matplotlib dependency; core runner uses standard library only.')
    args=parser.parse_args()
    try:
        print(render(args.report,args.plot).resolve())
    except ImportError as exc:
        raise SystemExit('Summary written. Optional plots need: python -m pip install "matplotlib>=3.8,<4"') from exc
