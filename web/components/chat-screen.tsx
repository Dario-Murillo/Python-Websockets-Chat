"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Wordmark } from "@/components/wordmark";
import { useChatSocket } from "@/hooks/use-chat-socket";
import { MAX_MESSAGE_LENGTH } from "@/lib/config";
import type { Room, Session, WsStatus } from "@/lib/types";

type Props = {
  session: Session;
  room: Room;
  onLeave: () => void;
  onLogout: () => void;
};

const STATUS_STYLES: Record<WsStatus, { dot: string; label: string }> = {
  connecting: { dot: "bg-warning animate-glow", label: "text-warning" },
  connected: {
    dot: "bg-success shadow-[0_0_6px_var(--color-success)]",
    label: "text-success",
  },
  disconnected: { dot: "bg-danger", label: "text-danger" },
};

export default function ChatScreen({ session, room, onLeave, onLogout }: Props) {
  const { status, messages, members, send } = useChatSocket(room.slug, session);
  const [text, setText] = useState("");

  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const list = listRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [messages]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) return;
    if (send(trimmed)) setText("");
  }

  const statusStyle = STATUS_STYLES[status];

  return (
    <div className="fixed inset-0 flex animate-fade-in">
      <aside className="flex h-full w-57.5 shrink-0 flex-col justify-between overflow-hidden border-r border-border bg-surface px-4 py-6">
        <div className="flex flex-col gap-7 overflow-hidden">
          <Wordmark size="sm" />

          <section className="flex flex-col">
            <SectionLabel>CHANNEL</SectionLabel>
            <div className="flex items-center gap-1 truncate text-[15px] font-medium">
              <span className="text-[1.1em] text-accent">#</span>
              {room.name}
            </div>
            <div className="mt-1 text-[11px] leading-snug text-muted">
              {room.description}
            </div>
          </section>

          <section className="flex flex-col">
            <SectionLabel>SIGNED IN AS</SectionLabel>
            <div className="flex items-center gap-2 text-[13px] text-accent2">
              <span className="size-1.75 shrink-0 rounded-full bg-success shadow-[0_0_6px_var(--color-success)]" />
              {session.username}
            </div>
          </section>

          <section className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <SectionLabel>ONLINE ({members.length})</SectionLabel>
            <ul className="scrollbar-slim flex max-h-45 flex-col gap-2 overflow-y-auto">
              {members.map((member) => {
                const isSelf = member === session.username;
                return (
                  <li
                    key={member}
                    className={`flex items-center gap-2 truncate text-xs ${
                      isSelf ? "text-accent2" : "text-muted"
                    }`}
                  >
                    <span
                      className={`size-1.25 shrink-0 rounded-full ${
                        isSelf
                          ? "bg-success shadow-[0_0_4px_var(--color-success)]"
                          : "bg-border"
                      }`}
                    />
                    {isSelf ? `${member} (you)` : member}
                  </li>
                );
              })}
            </ul>
          </section>
        </div>

        <div className="flex flex-col gap-2">
          <button
            type="button"
            onClick={onLeave}
            className="cursor-pointer rounded-sharp border border-border px-3 py-2 text-left text-[10px] tracking-[1px] text-muted transition-colors hover:border-accent2 hover:text-accent2"
          >
            ← ALL ROOMS
          </button>
          <button
            type="button"
            onClick={onLogout}
            className="cursor-pointer rounded-sharp border border-border px-3 py-1.75 text-left text-[10px] tracking-[1px] text-muted transition-colors hover:border-danger hover:text-danger"
          >
            LOGOUT
          </button>
        </div>
      </aside>

      <main className="flex h-full min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex shrink-0 items-center justify-between border-b border-border bg-surface px-6 py-4">
          <div className="flex items-center gap-1">
            <span className="text-[1.1em] text-accent">#</span>
            <span className="text-[15px] font-medium">{room.name}</span>
          </div>
          <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-[1.5px]">
            <span
              className={`size-1.5 shrink-0 rounded-full ${statusStyle.dot}`}
            />
            <span className={statusStyle.label}>{status}</span>
          </div>
        </header>

        <div
          ref={listRef}
          className="scrollbar-slim flex flex-1 flex-col gap-1 overflow-y-auto scroll-smooth p-6"
        >
          {messages.length === 0 ? (
            <div className="m-auto text-xs italic tracking-[1px] text-muted">
              No messages yet. Say something.
            </div>
          ) : (
            messages.map((message) =>
              message.system ? (
                <div
                  key={message.id}
                  className="animate-fade-in-fast rounded-sharp py-1.5 pl-2.5 pr-2.5 italic opacity-45"
                >
                  {message.text}
                </div>
              ) : (
                <div
                  key={message.id}
                  className="flex animate-fade-in-fast gap-3 rounded-sharp px-2.5 py-1.5 transition-colors hover:bg-surface2"
                >
                  <div className="flex min-w-18 shrink-0 flex-col items-end gap-0.5">
                    <span
                      className={`max-w-20 truncate text-[11px] font-medium ${
                        message.own ? "text-accent" : "text-accent2"
                      }`}
                    >
                      {message.author}
                    </span>
                    <span className="whitespace-nowrap text-[10px] text-muted">
                      {message.time}
                    </span>
                  </div>
                  <div className="min-h-4.5 w-px shrink-0 self-stretch bg-border" />
                  <div className="flex-1 wrap-break-word pt-px text-[13px] leading-relaxed">
                    {message.text}
                  </div>
                </div>
              ),
            )
          )}
        </div>

        <form
          onSubmit={handleSubmit}
          className="flex shrink-0 items-center gap-2.5 border-t border-border bg-surface px-6 py-4"
        >
          <input
            ref={inputRef}
            type="text"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder={`Message #${room.name}`}
            autoComplete="off"
            maxLength={MAX_MESSAGE_LENGTH}
            className="flex-1 rounded-sharp border border-border bg-bg px-3.5 py-2.5 text-[13px] text-text outline-none transition-colors placeholder:text-muted focus:border-accent"
          />
          <button
            type="submit"
            aria-label="Send message"
            className="flex size-10 shrink-0 cursor-pointer items-center justify-center rounded-sharp bg-accent text-bg transition-opacity hover:opacity-85 active:scale-94"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path
                d="M2 9L16 2L9 16L8 10L2 9Z"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </form>
      </main>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-1.5 text-[9px] tracking-[2.5px] text-muted">
      {children}
    </div>
  );
}
