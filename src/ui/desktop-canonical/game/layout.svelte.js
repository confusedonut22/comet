import { innerWidth, innerHeight } from "svelte/reactivity/window";
import { getContext, setContext } from "svelte";

const LAYOUT_CONTEXT_KEY = "jackchad.desktop-canonical.layout";

const STANDARD_MAIN_SIZES_MAP = {
  desktop: { width: 1920, height: 1080 },
};

const getRatio = (value) => value.width / (value.height || 1);

export const createLayout = (layoutOptions) => {
  const canvasSizes = () => ({ width: innerWidth.current ?? 1, height: innerHeight.current ?? 1 });
  const canvasRatio = () => getRatio(canvasSizes());
  const canvasRatioType = () => {
    if (canvasRatio() >= 1.3) return "longWidth";
    if (canvasRatio() <= 0.8) return "longHeight";
    return "almostSquare";
  };
  const canvasSizeType = () => {
    const deviceWidth = Math.min(canvasSizes().width, canvasSizes().height);
    if (deviceWidth <= 375) return "smallMobile";
    if (deviceWidth <= 480) return "mobile";
    if (deviceWidth <= 820) return "tablet";
    if (deviceWidth <= 1024) return "largeTablet";
    return "desktop";
  };
  const layoutType = () => "desktop";
  const isStacked = () => false;

  const createMainLayout = (mainSizesMap) => () => {
    const x = canvasSizes().width * 0.5;
    const y = canvasSizes().height * 0.5;
    const mainSizes = mainSizesMap.desktop ?? mainSizesMap[layoutType()];
    const widthScale = canvasSizes().width / mainSizes.width;
    const heightScale = canvasSizes().height / mainSizes.height;
    const scale = Math.min(widthScale, heightScale);

    return {
      x,
      y,
      scale,
      width: mainSizes.width,
      height: mainSizes.height,
      anchor: 0.5,
    };
  };

  const mainLayout = createMainLayout(layoutOptions.mainSizesMap);
  const mainLayoutStandard = createMainLayout(STANDARD_MAIN_SIZES_MAP);

  const createBackgroundLayout = ({ scale, ratio }) => {
    const ratioNow = getRatio(canvasSizes());

    if (ratioNow < ratio) {
      return {
        x: canvasSizes().width / 2,
        y: canvasSizes().height / 2,
        height: canvasSizes().height * scale,
      };
    }

    return {
      x: canvasSizes().width / 2,
      y: canvasSizes().height / 2,
      width: canvasSizes().width * scale,
    };
  };

  const normalBackgroundLayout = ({ scale }) =>
    createBackgroundLayout({ scale, ratio: layoutOptions.backgroundRatio.normal });
  const portraitBackgroundLayout = ({ scale }) =>
    createBackgroundLayout({ scale, ratio: layoutOptions.backgroundRatio.portrait });

  const stateLayout = $state({
    showLoadingScreen: true,
  });

  const stateLayoutDerived = {
    canvasSizes,
    canvasRatio,
    canvasRatioType,
    canvasSizeType,
    layoutType,
    isStacked,
    mainLayout,
    mainLayoutStandard,
    normalBackgroundLayout,
    portraitBackgroundLayout,
  };

  return {
    stateLayout,
    stateLayoutDerived,
  };
};

export const { stateLayout, stateLayoutDerived } = createLayout({
  backgroundRatio: {
    normal: 1.777,
    portrait: 0.5625,
  },
  mainSizesMap: STANDARD_MAIN_SIZES_MAP,
});

export const setContextLayout = (value = { stateLayout, stateLayoutDerived }) => {
  setContext(LAYOUT_CONTEXT_KEY, value);
  return value;
};

export const getContextLayout = () => getContext(LAYOUT_CONTEXT_KEY);

export const initializeLayoutContext = () =>
  setContextLayout({ stateLayout, stateLayoutDerived });
