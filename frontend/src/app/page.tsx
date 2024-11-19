"use client";
import { SignInButton, SignOutButton, useUser, useAuth, useSession } from "@clerk/nextjs";
import { useState, useEffect } from "react";

export default function Home() {
  const { user, isLoaded } = useUser();
  const { getToken } = useAuth();
  const { session } = useSession();
  const [token, setToken] = useState<string>("");
  const [sessionId, setSessionId] = useState<string>("");

  useEffect(() => {
    if (session) {
      setSessionId(session.id);
      getToken().then(setToken);
    }
  }, [session, getToken]);

  if (!isLoaded) return <div>Loading...</div>;

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      {!user ? (
        <SignInButton>
          <button className="bg-blue-500 text-white px-4 py-2 rounded">
            登录
          </button>
        </SignInButton>
      ) : (
        <div className="space-y-4 text-left max-w-2xl w-full">
          <div className="space-y-2 bg-gray-100 p-4 rounded">
            <p><strong>Clerk ID:</strong> {user.id}</p>
            <p><strong>Email:</strong> {user.emailAddresses[0]?.emailAddress}</p>
            <p><strong>Username:</strong> {user.username || '未设置'}</p>
            <div className="mt-4">
              <p><strong>Session ID:</strong></p>
              <textarea 
                readOnly 
                value={sessionId} 
                className="w-full mt-2 p-2 text-sm bg-white rounded h-12 font-mono"
              />
              <p className="mt-4"><strong>JWT Token:</strong></p>
              <textarea 
                readOnly 
                value={token} 
                className="w-full mt-2 p-2 text-sm bg-white rounded h-24 font-mono"
              />
            </div>
          </div>
          <SignOutButton>
            <button className="bg-red-500 text-white px-4 py-2 rounded">
              退出
            </button>
          </SignOutButton>
        </div>
      )}
    </main>
  );
}
