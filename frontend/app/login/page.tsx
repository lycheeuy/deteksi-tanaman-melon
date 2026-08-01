"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { isAxiosError } from "axios";
import { useForm } from "react-hook-form";
import { Leaf, Loader2, LogIn } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { setToken } from "@/lib/auth";
import api from "@/services/api";
import type { LoginResponse } from "@/types";

interface LoginFormValues {
  username: string;
  password: string;
}

/** Masa hidup cookie token: 24 jam (selaras masa berlaku JWT backend). */
const TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24;

function mapLoginError(err: unknown): string {
  if (isAxiosError(err) && err.response) {
    if (err.response.status === 401) return "Username atau password salah.";
    return "Terjadi kesalahan pada server.";
  }
  return "Backend tidak dapat dihubungi.";
}

function LoginForm(): React.ReactElement {
  const router = useRouter();
  const searchParams = useSearchParams();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>();

  const [isSubmitting, setIsSubmitting] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);

  const onSubmit = async (values: LoginFormValues): Promise<void> => {
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await api.post<LoginResponse>("/auth/login", values);
      setToken(response.data.access_token, TOKEN_MAX_AGE_SECONDS);
      // Kembali ke halaman asal (bila diarahkan middleware) atau dashboard.
      const from = searchParams.get("from");
      router.push(from && from.startsWith("/") ? from : "/");
      router.refresh();
    } catch (err: unknown) {
      setError(mapLoginError(err));
      setIsSubmitting(false);
    }
  };

  const inputClass =
    "h-9 w-full rounded-md border border-input bg-background px-3 text-sm " +
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

  return (
    <Card className="w-full max-w-sm">
      <CardHeader className="items-center text-center">
        <span className="mb-2 flex size-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
          <Leaf className="size-6" />
        </span>
        <CardTitle>Masuk ke Dashboard</CardTitle>
        <CardDescription>
          Gunakan username atau email beserta password Anda.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-4"
          onSubmit={(event) => void handleSubmit(onSubmit)(event)}
          noValidate
        >
          <div className="space-y-1.5">
            <label htmlFor="username" className="text-sm font-medium">
              Username / Email
            </label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              className={inputClass}
              disabled={isSubmitting}
              {...register("username", {
                required: "Username atau email wajib diisi.",
              })}
            />
            {errors.username ? (
              <p className="text-xs text-destructive">
                {errors.username.message}
              </p>
            ) : null}
          </div>

          <div className="space-y-1.5">
            <label htmlFor="password" className="text-sm font-medium">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              className={inputClass}
              disabled={isSubmitting}
              {...register("password", {
                required: "Password wajib diisi.",
              })}
            />
            {errors.password ? (
              <p className="text-xs text-destructive">
                {errors.password.message}
              </p>
            ) : null}
          </div>

          {error ? (
            <p className="text-sm font-medium text-destructive">{error}</p>
          ) : null}

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? <Loader2 className="animate-spin" /> : <LogIn />}
            {isSubmitting ? "Memproses…" : "Login"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default function LoginPage(): React.ReactElement {
  return (
    <div className="flex min-h-[70vh] items-center justify-center">
      <React.Suspense fallback={null}>
        <LoginForm />
      </React.Suspense>
    </div>
  );
}