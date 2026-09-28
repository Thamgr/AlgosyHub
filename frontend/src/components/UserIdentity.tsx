import UserAvatar from "./UserAvatar";
import { displayName, type UserDisplay } from "../lib/userDisplay";

export default function UserIdentity({ user }: { user: UserDisplay }) {
  return (
    <span className="inline-flex min-w-0 max-w-full items-center gap-2 align-middle">
      <UserAvatar user={user} />
      <span className="truncate">{displayName(user)}</span>
    </span>
  );
}
