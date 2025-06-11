"use client";

import Link from "next/link";
import { useAuth } from "@/context/auth-context";
import { Button } from "./ui/button";

export default function Navbar() {
  const { isAuthenticated, user, logout } = useAuth();

  return (
    <nav className="bg-background border-b">
      <div className="container mx-auto flex justify-between items-center p-4">
        <Link href="/" className="text-xl font-bold">
          OnePaper
        </Link>
        <div className="flex items-center gap-4">
          {isAuthenticated ? (
            <>
              <Link href="/library">
                <Button variant="ghost">My Library</Button>
              </Link>
              <span className="text-sm">
                Welcome, {user?.name || user?.email}
              </span>
              <Button onClick={logout} variant="outline">
                Logout
              </Button>
            </>
          ) : (
            <>
              <Link href="/login">
                <Button variant="ghost">Login</Button>
              </Link>
              <Link href="/register">
                <Button>Register</Button>
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
