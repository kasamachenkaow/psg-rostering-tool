export const ROLE_GRADIENTS: Record<string, string> = {
  Leader: 'from-amber-400/70 to-orange-500/40',
  Supervisor: 'from-emerald-400/70 to-teal-500/40',
  Technician: 'from-sky-400/70 to-indigo-500/40',
  Responder: 'from-rose-400/70 to-pink-500/40',
  default: 'from-neon-cyan/70 to-neon-blue/40',
};

export const ROLE_BADGES: Record<string, string> = {
  Leader: 'border-amber-300/40 bg-amber-300/10 text-amber-100',
  Supervisor: 'border-emerald-300/40 bg-emerald-300/10 text-emerald-100',
  Technician: 'border-sky-300/40 bg-sky-300/10 text-sky-100',
  Responder: 'border-rose-300/40 bg-rose-300/10 text-rose-100',
  default: 'border-cyan-300/30 bg-cyan-300/10 text-cyan-100',
};

export function getRoleGradient(role?: string | null): string {
  if (!role) return ROLE_GRADIENTS.default;
  return ROLE_GRADIENTS[role] ?? ROLE_GRADIENTS.default;
}

export function getRoleBadgeClass(role?: string | null): string {
  if (!role) return ROLE_BADGES.default;
  return ROLE_BADGES[role] ?? ROLE_BADGES.default;
}
