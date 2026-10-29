import { Link } from "react-router";

export function HelpPage() {
  return (
    <section className="stack narrow">
      <h1>Help</h1>
      <section className="panel">
        <h2>Make a part</h2>
        <p>
          Open a project from <Link to="/">Projects</Link>, describe the part with its sizes, and press
          Generate. Attach an image, a mesh or a spec file when the words are not enough. The timeline shows
          each step while the part is built and checked.
        </p>
      </section>
      <section className="panel">
        <h2>Change it</h2>
        <p>
          In the editor, edit a parameter and press Enter or Apply, or turn on Apply instantly. Select a
          component to aim a change request at it. Every change is a new version; older ones can be restored.
        </p>
      </section>
      <section className="panel">
        <h2>Give it context</h2>
        <p>
          The Context tab of a project takes specs, tables, drawings and notes. Facts and rules found in them
          are used by every generation in that project and shown in the knowledge graph.
        </p>
      </section>
      <section className="panel">
        <h2>Get the files</h2>
        <p>Export STEP, STL, GLB or the build script from the editor, or share a link to a version.</p>
      </section>
    </section>
  );
}
