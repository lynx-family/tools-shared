/*
 * Copyright (c) 2021, ByteDance CORPORATION. All rights reserved.
 */
package com.lynx.tasm;

import android.content.Context;
import android.graphics.Bitmap;
import android.view.KeyEvent;
import android.view.View;
import com.lynx.tasm.behavior.LynxUIOwner;
import java.lang.ref.WeakReference;

/**
 * RenderkitViewDelegate is an ability collection for self-rendering view.
 *
 * The consideration for this class is that renderkit related classes should be
 * excluded for platform-rendering build, so that reflection is needed when
 * using renderkit. This interface can avoid using too much reflections.
 */
public interface RenderkitViewDelegate {
  public enum RenderMode { SURFACE, TEXTURE, SYNC, DELEGATE }

  public void onEnterForeground();

  public void onEnterBackground();

  public void onDestroy();

  public boolean dispatchKeyEvent(KeyEvent event);

  public void takeScreenshot();

  public RenderMode getRenderMode();

  public long getNativePaintingContextPtr();

  public void reloadAndInit();

  public void attachLynxUIOwner(WeakReference<LynxUIOwner> uiOwner);
}
