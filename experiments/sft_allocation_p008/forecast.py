"""Result-blind engineering forecasts; monetary reservations are a separate gate."""
import math
from .contract import BRANCHES,BASE_CAP,run_roster,select_branch
RATE=4.393584/3600


def makespan(durations,capacity=4):
    slots=[0.]*capacity
    # Predeclared list scheduling. Do not divide total GPU seconds by four.
    for duration in durations:
        i=min(range(capacity),key=lambda n:slots[n]);slots[i]+=duration
    return max(slots),slots


def forecasts(old_runs,phase0,now_hour_pdt):
    if len(old_runs)!=8 or not phase0['four_gpu_verified']:raise ValueError('Full old timing and real concurrency required')
    if any(r['committed_updates']!=256 for r in old_runs):raise ValueError('Old timing dose differs')
    if phase0['teacher_outputs']!=1024 or phase0['teacher_batch_count']!=32:raise ValueError('Completed calibration required')
    train=sum(r['training_update_seconds'] for r in old_runs)/8
    residual=sum(r['other_worker_seconds'] for r in old_runs)/8
    # No assertion that residual means just inference: includes loading/checkpoint/I/O.
    per_attempt=phase0['teacher_active_seconds']/1024
    if train<=0 or residual<=0 or per_attempt<=0:raise ValueError('Invalid measured timings')
    answer=[]
    for branch in BRANCHES:
        rows=run_roster(*branch);draws=branch[2]
        # Reserve forecast teacher work at the full physical cap, not an assumed 8k yield.
        throughput_seconds=1.2*per_attempt*16384
        # At most two distinct policy actions per round: the wallets of a policy
        # share history until a cap stops them. Late rounds may contain only16.
        expected_rounds=math.ceil(BASE_CAP*branch[0]/(16*phase0['teacher_mean_prompt_output_tokens']))
        # Ten seconds of per-round metadata overhead is an explicit unmeasured
        # allowance for more wallet/guard records, not a benchmark result.
        round_seconds=1.2*expected_rounds*(phase0['teacher_batch_p95_seconds']+10.)
        pool_seconds=math.ceil(max(throughput_seconds,round_seconds)+phase0['teacher_load_seconds']+300)
        students={r['run_id']:math.ceil(1.2*(train*r['training_multiple']+residual)+120) for r in rows}
        base_seconds=math.ceil(1.2*residual+120)
        # Pools can overlap on two cards, but no student dispatch before both local corpora exist.
        # Allow G1 D1/D2 30 minutes each and full joint-plan build/export 30 minutes.
        before=pool_seconds+5400
        durations=[students[r['run_id']] for r in rows if r['role']=='main']+[base_seconds]+[students[r['run_id']] for r in rows if r['role']=='bridge']
        training_wall,slots=makespan(durations)
        after=7200  # local/independent final evidence review and corrective buffer before18PDT
        total_wall=before+training_wall+after
        # Phase0 cost is an observed lifecycle estimate with retained unresolved-cost allowance.
        # Never interpret this as invoice or use it instead of sum-of-hard-slot reservations.
        gpu_seconds=draws*pool_seconds+sum(students.values())+base_seconds
        cost=phase0['phase0_cost_upper_usd']+gpu_seconds*RATE+5. # CPU/storage/export allowance
        answer.append(dict(branch=list(branch),total_stage_usd_upper=cost,
          finish_hour_pdt_upper=now_hour_pdt+total_wall/3600,student_seconds=students,
          pool_seconds_per_draw=pool_seconds,base_seconds=base_seconds,
          stage_wall_seconds=total_wall,gpu_seconds_forecast=gpu_seconds,scheduled_lane_seconds=slots,
          timing_margin=1.2,teacher_attempts_per_draw_forecast=16384,teacher_rounds_estimate=expected_rounds,
          teacher_round_metadata_allowance_seconds=10.,teacher_full_cap_throughput_seconds=throughput_seconds,
          teacher_round_sensitivity_seconds={str(x):math.ceil(1.2*expected_rounds*(phase0['teacher_batch_p95_seconds']+x)+phase0['teacher_load_seconds']+300) for x in (5,10,20)},
          before_student_buffer_seconds=5400,after_student_buffer_seconds=after))
    return dict(training_unit_seconds_mean=train,other_worker_seconds_mean=residual,
        teacher_active_seconds_per_attempt=per_attempt,forecast_uses_no_main_outcomes=True,
        start_hour_pdt=now_hour_pdt,branches=answer,selected=select_branch(answer),
        reservations_still_require_separate_check=True,
        caveat='20% margin over measured averages is an engineering estimate, not a statistical confidence bound or invoice.')
