'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AnalysisState {
  _hasHydrated: boolean;
  companyId: string;
  companyName: string;
  uploadedFileNames: string[];
  pipelineStatus: 'idle' | 'running' | 'hitl' | 'complete' | 'error';
  pipelineStep: number; // 0=upload, 1=notes, 2=pipeline, 3=outputs
  scoreResult: any | null;
  result: any | null;
  explanation: any | null;
  research: any[];
  setCompany: (id: string, name: string) => void;
  setUploadedFileNames: (names: string[]) => void;
  setPipelineStatus: (status: AnalysisState['pipelineStatus']) => void;
  setPipelineStep: (step: number) => void;
  advanceStep: () => void;
  canAccess: (step: number) => boolean;
  setScoreResult: (score: any) => void;
  setResult: (result: any) => void;
  setExplanation: (explanation: any) => void;
  setResearch: (research: any[]) => void;
  reset: () => void;
  setHasHydrated: (state: boolean) => void;
}

const INITIAL: Pick<
  AnalysisState,
  '_hasHydrated' | 'companyId' | 'companyName' | 'uploadedFileNames' | 'pipelineStatus' | 'pipelineStep' | 'scoreResult' | 'result' | 'explanation' | 'research'
> = {
  _hasHydrated: false,
  companyId: '',
  companyName: '',
  uploadedFileNames: [],
  pipelineStatus: 'idle',
  pipelineStep: 0,
  scoreResult: null,
  result: null,
  explanation: null,
  research: [],
};

export const useAnalysisStore = create<AnalysisState>()(
  persist(
    (set, get) => ({
      ...INITIAL,
      setCompany: (id, name) => set({ companyId: id, companyName: name }),
      setUploadedFileNames: (names) => set({ uploadedFileNames: names }),
      setPipelineStatus: (status) => set({ pipelineStatus: status }),
      setPipelineStep: (step) => set({ pipelineStep: step }),
      advanceStep: () => set((state) => ({ pipelineStep: Math.min(3, state.pipelineStep + 1) })),
      canAccess: (step) => get().pipelineStep >= step,
      setScoreResult: (score) => set({ scoreResult: score }),
      setResult: (result) => set({ result }),
      setExplanation: (explanation) => set({ explanation }),
      setResearch: (research) => set({ research }),
      reset: () => {
        document.cookie = 'ic_session=; path=/; max-age=0';
        set((state) => ({ ...INITIAL, _hasHydrated: state._hasHydrated })); // retain hydration flag
      },
      setHasHydrated: (state) => set({ _hasHydrated: state }),
    }),
    {
      name: 'ob-analysis-store',
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
