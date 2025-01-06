import * as React from "react";
import type {
  ExampleCategory,
  ExampleItem,
  ExamplePosition,
} from "../examples";
import {
  findExampleByTitle,
  getExampleCategories,
  sanitizeTitleForUrl,
} from "../examples";
import type { AppEngine } from "./App";
import "./ExampleSelector.css";
import type { FileContent } from "./filecontent";

export function ExampleSelector({
  setCurrentFiles,
  filesHaveChanged,
  startWithSelectedExample,
  appEngine,
}: {
  setCurrentFiles: React.Dispatch<React.SetStateAction<FileContent[]>>;
  filesHaveChanged: boolean;
  startWithSelectedExample?: string;
  appEngine: AppEngine;
}) {
  const [currentSelection, setCurrentSelection] =
    React.useState<ExamplePosition | null>(null);

  // This starts null; will be set by a useEffect which calls an async function.
  const [exampleCategories, setExampleCategories] = React.useState<
    ExampleCategory[] | null
  >(null);

  React.useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-floating-promises
    (async () => {
      const categories = (await getExampleCategories(appEngine)).filter(
        // Exclude the "Editor" category from the general examples list
        (cat) => cat.category !== "Editor",
      );
      setExampleCategories(categories);
    })();
  }, [appEngine]);

  // If we were told to start with a specific example, find it and select it.
  React.useEffect(() => {
    if (!startWithSelectedExample) return;
    if (!exampleCategories) return;

    let position = findExampleByTitle(
      startWithSelectedExample,
      exampleCategories,
    );
    if (!position) {
      position = { categoryIndex: 0, index: 0 };
    }
    setCurrentSelection(position);
  }, [startWithSelectedExample, exampleCategories]);

  const setFilesForApp = React.useCallback(
    ({ categoryIndex, index }: ExamplePosition) => {
      if (!exampleCategories) return;
      setCurrentFiles(exampleCategories[categoryIndex].apps[index].files);
    },
    [exampleCategories, setCurrentFiles],
  );

  const chooseExample = React.useCallback(
    ({ categoryIndex, index }: ExamplePosition) => {
      if (!exampleCategories) return;
      if (filesHaveChanged) {
        if (!confirm("Discard all changes to files?")) return;
      }
      const example = exampleCategories[categoryIndex].apps[index];

      setCurrentSelection({ categoryIndex, index });
      setExampleUrlHash(example.title);
    },
    [filesHaveChanged, exampleCategories, setCurrentSelection],
  );

  // Keep app up-to-date with current selection
  React.useEffect(() => {
    if (!currentSelection) return;
    setFilesForApp(currentSelection);
  }, [currentSelection, setFilesForApp]);

  function renderExampleItem({
    item,
    index,
    categoryIndex,
  }: {
    item: ExampleItem;
    index: number;
    categoryIndex: number;
  }) {
    let isSelected: boolean;
    if (!currentSelection) {
      isSelected = false;
    } else {
      isSelected =
        currentSelection.categoryIndex === categoryIndex &&
        currentSelection.index === index;
    }

    // Use the React. Fragment component instead of <></> so we can use the key prop
    return (
      <React.Fragment key={item.title}>
        <div className={"example" + (isSelected ? " selected" : "")}>
          <a
            href={buildUrlForExample(item.title)}
            onClick={(e) => {
              // Holding down the command key and clicking will open example in
              // a new browser. If this happens we don't want to update the
              // current app as well so we will exit early
              const newTabClick = e.metaKey;
              if (newTabClick) return;

              // Given this is a normal click we want to override the defaults
              // of the link so we don't trigger a page refresh
              e.preventDefault();

              // Clicking on a selected example wont do anything so don't even
              // mess with the state
              if (isSelected) return;
              chooseExample({ categoryIndex, index });
            }}
          >
            <h4 className="title">{item.title}</h4>
            <p className="about">{item.about}</p>
          </a>
        </div>
        <div className="divider" />
      </React.Fragment>
    );
  }

  return (
    <div className="shinylive-example-selector">
      <div className="categories">
        <h2>Examples</h2>
        {exampleCategories?.map(({ category, apps }, categoryIndex) => (
          <section key={category}>
            <h3 className="category-title">{category}</h3>
            {apps.map((item, index) =>
              renderExampleItem({ item, index, categoryIndex }),
            )}
          </section>
        ))}
      </div>
    </div>
  );
}

function setExampleUrlHash(title: string): void {
  window.location.hash = "#" + sanitizeTitleForUrl(title);
}

function buildUrlForExample(title: string) {
  return (
    window.location.origin +
    window.location.pathname +
    "#" +
    sanitizeTitleForUrl(title)
  );
}
