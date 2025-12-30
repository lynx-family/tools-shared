//  Original
//  files:https://github.com/BigBadaboom/androidsvg/blob/master/androidsvg/src/main/java/com/caverock/androidsvg/utils/CanvasLegacy.java

/*
   Copyright 2013 Paul LeBeau, Cave Rock Software Ltd.
   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at
       http://www.apache.org/licenses/LICENSE-2.0
   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

   This file may have been modified by ByteDance Ltd. and/or its affiliates.
*/
package com.lynx.component.svg.parser;

import android.graphics.Canvas;
import java.lang.reflect.Method;

/**
 * "it's gone": Canvas#save(int) has been removed from sdk-28,
 * so this helper classes uses reflection to access the API on older devices.
 */
