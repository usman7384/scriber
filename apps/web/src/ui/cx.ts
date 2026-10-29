export const cx = (...names: (string | false | undefined)[]) => names.filter(Boolean).join(" ");
