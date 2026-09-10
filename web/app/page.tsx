"use client";

import { useRouter } from "next/navigation";
import AuthScreen from "@/components/auth-screen";
import RoomsScreen from "@/components/rooms-screen";
import Splash from "@/components/splash";
import { useAuth } from "@/hooks/use-auth";

export default function Home() {
  const { session, ready, error, isLoading, login, register, logout, clearError } =
    useAuth();
  const router = useRouter();

  // Hold the first paint until the stored session has been read, so a returning
  // user never sees the auth screen flash before the room list.
  if (!ready) return <Splash />;

  if (!session) {
    return (
      <AuthScreen
        error={error}
        isLoading={isLoading}
        onLogin={login}
        onRegister={register}
        onClearError={clearError}
      />
    );
  }

  return (
    <RoomsScreen
      session={session}
      onJoin={(room) => router.push(`/room/${room.slug}`)}
      onLogout={() => void logout()}
    />
  );
}
