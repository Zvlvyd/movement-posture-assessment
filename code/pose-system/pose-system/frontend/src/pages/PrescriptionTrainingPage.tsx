import { useEffect, useState, useCallback } from "react";
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
  const [completedExercises, setCompletedExercises] = useState<Set<string>>(new Set());
  const [result, setResult] = useState<LearningComplete | null>(null);

  // Training hook
  const [sessionState, sessionActions] = useTrainingSession({
    actionName: currentItem?.action_name || "",
    onComplete: (data) => {
      if (currentItem) {
        setCompletedExercises(prev => new Set(prev).add(currentItem.action_name));
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

  // Handlers
  const handleSelectPlan = useCallback((plan: PlanV2) => {
    setSelectedPlan(plan);
    setCompletedExercises(new Set());
    setMode("plan_detail");
  }, []);

  const handleStartExercise = useCallback(async (item: PlanItemV2) => {
    setCurrentItem(item);
    const ok = await sessionActions.startSession();
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
        completedExercises={completedExercises}
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
        completedCount={completedExercises.size}
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
