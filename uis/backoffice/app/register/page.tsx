import RegisterForm from "@/components/auth/RegisterForm";

export default function RegisterPage(): React.JSX.Element {
  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-10">
      <RegisterForm />
    </main>
  );
}
