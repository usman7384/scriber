import { useCallback } from "react";
import { useLocation, useNavigate, type Location } from "react-router";

export type SheetName = "settings" | "help";

interface SheetState {
  backdrop?: Location;
}

const home = { pathname: "/", search: "", hash: "", state: null, key: "home" } satisfies Location;

export const sheetOf = (pathname: string): SheetName | undefined =>
  pathname === "/settings" ? "settings" : pathname === "/help" ? "help" : undefined;

// The page a sheet floats over: the one it was opened from, or Home for a deep link.
export const backdropOf = (location: Location): Location =>
  sheetOf(location.pathname) ? ((location.state as SheetState | null)?.backdrop ?? home) : location;

export function useOpenSheet() {
  const location = useLocation();
  const navigate = useNavigate();
  return useCallback(
    (name: SheetName) =>
      navigate(`/${name}`, {
        state: sheetLinkState(location),
        replace: sheetOf(location.pathname) !== undefined,
      }),
    [location, navigate],
  );
}

export function useCloseSheet() {
  const location = useLocation();
  const navigate = useNavigate();
  const opened = (location.state as SheetState | null)?.backdrop !== undefined;
  return () => (opened ? navigate(-1) : navigate("/", { replace: true }));
}

export const sheetLinkState = (location: Location): SheetState => ({ backdrop: backdropOf(location) });
