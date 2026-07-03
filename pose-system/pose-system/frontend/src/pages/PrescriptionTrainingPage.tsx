import { useEffect, useState, useCallback, useRef } from "react";
import { message, Result, Button, Empty } from "antd";
import { prescriptionV2Api, learningApi } from "../services/api";
import { useTrainingSession } from "../hooks/useTrainingSession";
import TrainingSessionPanel from "../components/TrainingSessionPanel";
import PlanListPanel from "./training/PlanListPanel";
import PlanDetailPanel from "./training/PlanDetailPanel";
import TrainingResultPanel from "./training/TrainingResultPanel";
import type { PlanV2, PlanItemV2, LearningComplete } from "../types";

type PageMode = "plan_list" | "plan_detail" | "training" | "result";

export default function PrescriptionTrainingPage() {
  const [mode, setMode] = useState<PageMode>("plan_list");
  const [plans, setPlans] = useState<PlanV2[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<PlanV2 | null>(null);
  const [currentItem, setCurrentItem] = useState<PlanItemV2 | null>(null);
  const [completedItems, setCompletedItems] = useState<Set<number>>(new Set());
  const [itemProgress, setItemProgress] = useState<Map<number, { sets_done: number; total_sets: number; latest_reps: number; latest_score: number }>>(new Map());
  const [result, setResult] = useState<LearningComplete | null>(null);

  // 用 ref 避免 onComplete 中的闭包过期
  const currentItemRef = useRef<PlanItemV2 | null>(null);
  const selectedPlanRef = useRef<PlanV2 | null>(null);
  useEffect(() => { currentItemRef.current = currentItem; }, [currentItem]);
  useEffect(() => { selectedPlanRef.current = selectedPlan; }, [selectedPlan]);

  // 刷新进度
  const refreshProgress = useCallback(async (planId: number) => {
    try {
      const progress = await prescriptionV2Api.getProgress(planId);
      const map = new Map<number, any>();
      progress.items.forEach(p => map.set(p.plan_item_id, p));
      setItemProgress(map);
      setCompletedItems(new Set(progress.completed_item_ids));
    } catch { /* ignore */ }
  }, []);

  // Training hook
  const [sessionState, sessionActions] = useTrainingSession({
    actionName: currentItem?.action_name || "",
    onComplete: async (data) => {
      const item = currentItemRef.current;
      const plan = selectedPlanRef.current;
      if (item && plan) {
        // 保存到后端
        try {
          await prescriptionV2Api.saveProgress({
            plan_id: plan.id,
            plan_item_id: item.id,
            action_name: item.action_name,
            best_score: data.best_score,
            rep_count: data.rep_count || 0,
            hold_time_seconds: data.hold_time || 0,
            duration_seconds: data.duration,
          });
        } catch { /* 保存失败不阻碍流程 */ }
      }
      setResult(data);
      setMode("result");
    },
    onError: (msg) => message.error(msg),
  });

  // Data
  const loadPlans = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const r = await prescriptionV2Api.list();
      setPlans((r.plans || []).filter(p => p.status === "active"));
    } catch {
      setPlans([]);
      setLoadError(true);
      message.error("加载训练计划失败，请检查网络连接");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { loadPlans(); }, [loadPlans]);

  // 每次进入计划详情页时刷新进度
  useEffect(() => {
    if (mode === "plan_detail" && selectedPlan) {
      refreshProgress(selectedPlan.id);
    }
  }, [mode, selectedPlan, refreshProgress]);

  // Handlers
  const handleSelectPlan = useCallback(async (plan: PlanV2) => {
    setSelectedPlan(plan);
    // 从后端加载进度
    try {
      const progress = await prescriptionV2Api.getProgress(plan.id);
      setCompletedItems(new Set(progress.completed_item_ids));
      const map = new Map<number, any>();
      progress.items.forEach(p => map.set(p.plan_item_id, p));
      setItemProgress(map);
    } catch {
      setCompletedItems(new Set());
      setItemProgress(new Map());
    }
    setMode("plan_detail");
  }, []);

  const handleStartExercise = useCallback(async (item: PlanItemV2) => {
    setCurrentItem(item);
    // 获取动作的正确视角（避免闭包过期导致 actionName 为空）
    let view = "正面";
    try {
      const detail = await learningApi.getLearnableDetail(item.action_name);
      view = detail?.views?.[0] || "正面";
    } catch { /* use default */ }
    const ok = await sessionActions.startSession(view, item.action_name);
    if (ok) setMode("training");
  }, [sessionActions]);

  const handleExitTraining = useCallback(() => {
    sessionActions.endSession();
    setMode("plan_detail");
  }, [sessionActions]);

  const handleNextExercise = useCallback(() => setMode("plan_detail"), []);
  const handleAllPlans = useCallback(() => { setMode("plan_list"); loadPlans(); }, [loadPlans]);

  // Render
  if (mode === "plan_list") {
    if (loadError && !loading && plans.length === 0) {
      return (
        <Result
          status="warning"
          title="无法加载训练计划"
          subTitle="请检查网络连接后重试"
          extra={<Button type="primary" onClick={loadPlans}>重试</Button>}
        />
      );
    }
    if (!loading && plans.length === 0) {
      return (
        <Empty
          description="暂无活跃的训练计划"
          style={{ marginTop: 80 }}
        >
          <Button type="primary" onClick={() => { window.location.href = '/prescription'; }}>
            去评估获取训练计划
          </Button>
        </Empty>
      );
    }
    return <PlanListPanel plans={plans} loading={loading} onSelectPlan={handleSelectPlan} />;
  }

  if (mode === "plan_detail" && selectedPlan) {
    return (
      <PlanDetailPanel
        plan={selectedPlan}
        completedItems={completedItems}
        itemProgress={itemProgress}
        onBack={() => setMode("plan_list")}
        onStartExercise={handleStartExercise}
      />
    );
  }

  if (mode === "training") {
    return (
      <TrainingSessionPanel
        state={sessionState}
        actions={sessionActions}
        exerciseInfo={currentItem ? {
          name: currentItem.action_name,
          sets: currentItem.sets,
          reps: currentItem.reps,
          durationSeconds: currentItem.duration_seconds,
          notes: currentItem.notes,
        } : undefined}
        onExit={handleExitTraining}
      />
    );
  }

  if (mode === "result" && result && selectedPlan) {
    return (
      <TrainingResultPanel
        result={result}
        plan={selectedPlan}
        completedCount={completedItems.size}
        totalCount={selectedPlan.items?.length || 0}
        onBackToPlan={() => setMode("plan_detail")}
        onNextExercise={handleNextExercise}
        onAllPlans={handleAllPlans}
      />
    );
  }

  // Fallback for unexpected state — redirect to plan list
  return <PlanListPanel plans={plans} loading={loading} onSelectPlan={handleSelectPlan} />;
}
