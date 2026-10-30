import type { ReactNode } from "react";
import type { Project } from "../api";
import { HomeNav } from "./HomeNav";
import "./home.css";

interface Props {
  projects?: Project[] | undefined;
  current?: Project | undefined;
  allCurrent?: boolean;
  children: ReactNode;
}

export function HomeLayout({ projects = [], current, allCurrent, children }: Props) {
  return (
    <div className="home">
      <HomeNav projects={projects} current={current} allCurrent={allCurrent} />
      <main className="home-main">{children}</main>
    </div>
  );
}
