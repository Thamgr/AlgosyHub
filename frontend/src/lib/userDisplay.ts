export interface UserDisplay {
  username: string;
  full_name?: string;
  avatar_emoji?: string;
}

export function displayName(user: UserDisplay): string {
  return user.full_name?.trim() || user.username;
}

export function userInitials(user: UserDisplay): string {
  return displayName(user).split(/\s+/).slice(0, 2).map((part) => Array.from(part)[0]).join("").toLocaleUpperCase();
}
