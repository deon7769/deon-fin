import { ApiError } from "./api";
import type { AuthSession, LoginRequest } from "./types";

type RedirectTarget = {
  assign: (url: string) => void;
};

type SubmitLoginOptions = {
  input: LoginRequest;
  login: (input: LoginRequest) => Promise<AuthSession>;
  redirect: (url: string) => void;
  setPending: (pending: boolean) => void;
  setError: (message: string | null) => void;
};

export function loginErrorMessage(error: unknown) {
  if (error instanceof ApiError && error.status === 401) {
    return "E-mail ou senha invalidos.";
  }
  return error instanceof Error ? error.message : "Nao foi possivel entrar.";
}

export function redirectAfterLogin(url = "/", target?: RedirectTarget) {
  const destination =
    target ??
    (typeof window === "undefined"
      ? null
      : {
          assign: window.location.assign.bind(window.location),
        });

  destination?.assign(url);
}

export async function submitLogin({
  input,
  login,
  redirect,
  setPending,
  setError,
}: SubmitLoginOptions) {
  setPending(true);
  setError(null);
  try {
    await login(input);
    redirect("/");
  } catch (loginError) {
    setError(loginErrorMessage(loginError));
  } finally {
    setPending(false);
  }
}
