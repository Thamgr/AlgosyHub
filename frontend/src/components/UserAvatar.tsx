import { userInitials, type UserDisplay } from "../lib/userDisplay";

export default function UserAvatar({ user, size = "sm" }: { user: UserDisplay; size?: "sm" | "md" | "lg" }) {
  const sizing = size === "lg" ? "h-16 w-16 text-4xl" : size === "md" ? "h-10 w-10 text-2xl" : "h-7 w-7 text-lg";
  return (
    <span aria-hidden="true" className={`inline-flex shrink-0 items-center justify-center rounded-full bg-gray-100 leading-none ${sizing}`}>
      {user.avatar_emoji || <span className={size === "lg" ? "text-xl font-medium text-gray-500" : "text-xs font-medium text-gray-500"}>{userInitials(user)}</span>}
    </span>
  );
}
