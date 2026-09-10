"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useEffect } from "react";
import ChatScreen from "@/components/chat-screen";
import Splash from "@/components/splash";
import { Wordmark } from "@/components/wordmark";
import { useAuth } from "@/hooks/use-auth";
import { useRooms } from "@/hooks/use-rooms";
import type { Session } from "@/lib/types";

export default function RoomPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = use(params);
  const { session, ready, logout } = useAuth();
  const router = useRouter();

  // Also covers logout: clearing the session drops `session` to null and this
  // sends the user home. No `?next=` round trip — signing in lands on the room
  // list and the room gets picked again.
  useEffect(() => {
    if (ready && !session) router.replace("/");
  }, [ready, session, router]);

  if (!ready || !session) return <Splash />;

  return <Room slug={slug} session={session} onLogout={logout} />;
}

function Room({
  slug,
  session,
  onLogout,
}: {
  slug: string;
  session: Session;
  onLogout: () => void;
}) {
  const { rooms, error, isLoading } = useRooms(session.token);
  const router = useRouter();

  if (isLoading) return <Splash />;

  // Told apart on purpose: an unreachable API is not the same as a room that
  // does not exist, and saying "no such room" when the server is down sends the
  // user looking for the wrong problem.
  if (error) {
    return <Notice title="Could not load the channels" detail={error} />;
  }

  const room = rooms.find((candidate) => candidate.slug === slug);

  if (!room) {
    return (
      <Notice
        title={`No channel called #${slug}`}
        detail="The link may be wrong, or the channel is gone."
      />
    );
  }

  return (
    <ChatScreen
      // This page is reused when only the dynamic param changes, so the remount
      // `useChatSocket` requires has to come from here.
      key={slug}
      session={session}
      room={room}
      onLeave={() => router.push("/")}
      onLogout={onLogout}
    />
  );
}

function Notice({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="fixed inset-0 flex animate-fade-in items-center justify-center px-8">
      <div className="flex max-w-100 flex-col items-center gap-4 text-center">
        <Wordmark />
        <h1 className="font-display text-3xl tracking-[3px] text-danger">{title}</h1>
        <p className="text-xs leading-normal text-muted">{detail}</p>
        <Link
          href="/"
          className="mt-2 rounded-sharp border border-border px-3 py-1.5 text-[10px] tracking-[1.5px] text-muted transition-colors hover:border-accent hover:text-accent"
        >
          BACK TO CHANNELS
        </Link>
      </div>
    </div>
  );
}
