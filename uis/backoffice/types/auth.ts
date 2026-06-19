export interface AuthUser {
  id: number;
  email: string;
  name: string | null;
  is_active: boolean;
  is_admin: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserUpdateInput {
  email?: string;
  password?: string;
  name?: string;
  is_active?: boolean;
  is_admin?: boolean;
}

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";
