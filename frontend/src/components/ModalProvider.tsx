"use client";

import React, { createContext, useCallback, useContext, useMemo, useState } from "react";

type ModalKind = "alert" | "confirm";

type ModalState =
  | {
      open: true;
      kind: ModalKind;
      title: string;
      message: string;
      confirmText?: string;
      cancelText?: string;
      resolve?: (v: boolean) => void;
    }
  | { open: false };

type ModalApi = {
  alert: (message: string, opts?: { title?: string; confirmText?: string }) => Promise<void>;
  confirm: (message: string, opts?: { title?: string; confirmText?: string; cancelText?: string }) => Promise<boolean>;
};

const Ctx = createContext<ModalApi | null>(null);

function Backdrop({ onClose }: { onClose: () => void }) {
  return <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />;
}

function ModalCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div className="relative w-full max-w-md rounded-xl border border-zinc-600 bg-zinc-900 shadow-2xl">
        {children}
      </div>
    </div>
  );
}

export function ModalProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<ModalState>({ open: false });

  const close = useCallback((result: boolean) => {
    setState((s) => {
      if (s.open && s.resolve) {
        try {
          s.resolve(result);
        } catch {
          /* ignore */
        }
      }
      return { open: false };
    });
  }, []);

  const api = useMemo<ModalApi>(
    () => ({
      alert: (message, opts) =>
        new Promise<void>((resolve) => {
          setState({
            open: true,
            kind: "alert",
            title: opts?.title ?? "Info",
            message,
            confirmText: opts?.confirmText ?? "OK",
            resolve: () => resolve(),
          });
        }),
      confirm: (message, opts) =>
        new Promise<boolean>((resolve) => {
          setState({
            open: true,
            kind: "confirm",
            title: opts?.title ?? "Konfirmasi",
            message,
            confirmText: opts?.confirmText ?? "Ya",
            cancelText: opts?.cancelText ?? "Batal",
            resolve,
          });
        }),
    }),
    []
  );

  return (
    <Ctx.Provider value={api}>
      {children}

      {state.open && (
        <>
          <Backdrop onClose={() => close(false)} />
          <ModalCard>
            <div className="p-5">
              <div className="text-base font-semibold text-white">{state.title}</div>
              <div className="mt-2 text-sm text-zinc-300 whitespace-pre-wrap">{state.message}</div>

              <div className="mt-5 flex items-center justify-end gap-2">
                {state.kind === "confirm" && (
                  <button
                    onClick={() => close(false)}
                    className="px-4 py-2 rounded-lg border border-zinc-600 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-sm"
                  >
                    {state.cancelText ?? "Batal"}
                  </button>
                )}
                <button
                  onClick={() => close(true)}
                  className="px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black font-medium text-sm"
                >
                  {state.confirmText ?? "OK"}
                </button>
              </div>
            </div>
          </ModalCard>
        </>
      )}
    </Ctx.Provider>
  );
}

export function useModal() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useModal must be used within ModalProvider");
  return ctx;
}

