/*
 * Copyright 2023 The Lynx Authors. All rights reserved.
 *
 */

package com.lynx.tasm.behavior;

import static org.mockito.Mockito.spy;

import android.util.Log;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import com.lynx.tasm.LynxView;
import com.lynx.tasm.LynxViewBuilder;
import com.lynx.tasm.behavior.ui.LynxBaseUI;
import com.lynx.tasm.behavior.ui.UIBody;
import com.lynx.tasm.core.LynxThreadPool;
import com.lynx.tasm.utils.UIThreadUtils;
import com.lynx.testing.base.TestingUtils;
import java.lang.reflect.Field;
import java.util.HashMap;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
