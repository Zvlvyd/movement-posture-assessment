import { useEffect, useState, useCallback } from "react";
import { message } from "antd";
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
    try {
      const r = await prescriptionV2Api.list();
      setPlans((r.plans || []).filter(p => p.status === "active"));
    } catch { setPlans([]); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadPlans(); }, [loadPlans]);

  // Handlers
  const handleSelectPlan = (plan: PlanV2) => {
    setSelectedPlan(plan);
    setCompletedExercises(new Set());
    setMode("plan_detail");
  };

  const handleStartExercise = async (item: PlanItemV2) => {
    setCurrentItem(item);
    const ok = await sessionActions.startSession();
    if (ok) setMode("training");
  };

  const handleExitTraining = () => {
    sessionActions.endSession();
    setMode("plan_detail");
  };

  const handleNextExercise = () => setMode("plan_detail");
  const handleAllPlans = () => { setMode("plan_list"); loadPlans(); };

  // Render
  if (mode === "plan_list") {
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

  return null;
}
