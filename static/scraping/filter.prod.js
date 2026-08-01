function _array_like_to_array(arr, len) {
    if (len == null || len > arr.length)
        len = arr.length;
    for (var i = 0, arr2 = new Array(len); i < len; i++)
        arr2[i] = arr[i];
    return arr2
}
function _array_with_holes(arr) {
    if (Array.isArray(arr))
        return arr
}
function _array_without_holes(arr) {
    if (Array.isArray(arr))
        return _array_like_to_array(arr)
}
function _iterable_to_array(iter) {
    if (typeof Symbol !== "undefined" && iter[Symbol.iterator] != null || iter["@@iterator"] != null)
        return Array.from(iter)
}
function _iterable_to_array_limit(arr, i) {
    var _i = arr == null ? null : typeof Symbol !== "undefined" && arr[Symbol.iterator] || arr["@@iterator"];
    if (_i == null)
        return;
    var _arr = [];
    var _n = true;
    var _d = false;
    var _s, _e;
    try {
        for (_i = _i.call(arr); !(_n = (_s = _i.next()).done); _n = true) {
            _arr.push(_s.value);
            if (i && _arr.length === i)
                break
        }
    } catch (err) {
        _d = true;
        _e = err
    } finally {
        try {
            if (!_n && _i["return"] != null)
                _i["return"]()
        } finally {
            if (_d)
                throw _e
        }
    }
    return _arr
}
function _non_iterable_rest() {
    throw new TypeError("Invalid attempt to destructure non-iterable instance.\\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.")
}
function _non_iterable_spread() {
    throw new TypeError("Invalid attempt to spread non-iterable instance.\\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.")
}
function _sliced_to_array(arr, i) {
    return _array_with_holes(arr) || _iterable_to_array_limit(arr, i) || _unsupported_iterable_to_array(arr, i) || _non_iterable_rest()
}
function _to_consumable_array(arr) {
    return _array_without_holes(arr) || _iterable_to_array(arr) || _unsupported_iterable_to_array(arr) || _non_iterable_spread()
}
function _unsupported_iterable_to_array(o, minLen) {
    if (!o)
        return;
    if (typeof o === "string")
        return _array_like_to_array(o, minLen);
    var n = Object.prototype.toString.call(o).slice(8, -1);
    if (n === "Object" && o.constructor)
        n = o.constructor.name;
    if (n === "Map" || n === "Set")
        return Array.from(n);
    if (n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n))
        return _array_like_to_array(o, minLen)
}
var handle_select_carrera = function(event) {
    if (event.target.dataset.evref !== "handle_select_carrera")
        return;
    if (exist_item_on_selected("selected_carreras_menu", parseInt(event.target.querySelector("input").value))) {
        event.preventDefault();
        return
    }
    handle_select_menu(event, "preview-carreras", "selected_carreras_menu", "carreras_count");
    event.preventDefault()
};
var handle_unselect_carrera = function(event) {
    if (event.target.dataset.evref !== "handle_select_carrera")
        return;
    handle_unselect_menu(event, "preview-carreras", "selected_carreras_menu", "carreras_count", "carreras_menu")
};
var timeout_search_carrera = null;
var handle_input_search_carrera = function(event) {
    var carreras_menu_element = document.getElementById("carreras_menu");
    if (!carreras_menu_element || !Array.isArray(carreras))
        return;
    clearTimeout(timeout_search_carrera);
    timeout_search_carrera = setTimeout(function() {
        var _event_target_value_normalize_replace, _event_target_value;
        var pattern_value = (_event_target_value = event.target.value) === null || _event_target_value === void 0 ? void 0 : (_event_target_value_normalize_replace = _event_target_value.normalize("NFD").replace(/[\u0300-\u036f]/g, "")) === null || _event_target_value_normalize_replace === void 0 ? void 0 : _event_target_value_normalize_replace.trim();
        var pattern = new RegExp(pattern_value,"i");
        var filter = carreras.filter(function(carrera) {
            var _carrera_nombre;
            return pattern.test((_carrera_nombre = carrera.nombre) === null || _carrera_nombre === void 0 ? void 0 : _carrera_nombre.normalize("NFD").replace(/[\u0300-\u036f]/g, ""))
        }).slice(0, 10);
        if (filter.length > 0) {
            var menu_content = "                \n                ".concat(filter.map(function(carrera) {
                return exist_item_on_selected("selected_carreras_menu", carrera.id) ? "" : '\n                    <label class="block text-slate-300 cursor-pointer hover:bg-slate-600 w-full" data-evref="handle_select_carrera" data-nombre="'.concat(carrera.nombre, '">\n                        <input type="checkbox" class="pointer-events-none" name="carreras[]" value="').concat(carrera.id, '">\n                        <span class="pointer-events-none w-full">').concat(carrera.nombre, "</span>\n                    </label>")
            }).join(""), "\n            ");
            carreras_menu_element.innerHTML = menu_content
        } else {
            carreras_menu_element.innerHTML = '<li class="pb-1 text-slate-300 cursor-not-allowed">Sin resultados</li>'
        }
    }, 300)
};
var handle_select_institucion = function(event) {
    if (event.target.dataset.evref !== "handle_select_institucion")
        return;
    if (exist_item_on_selected("selected_institucion_menu", parseInt(event.target.querySelector("input").value))) {
        event.preventDefault();
        return
    }
    handle_select_menu(event, "preview-instituciones", "selected_institucion_menu", "institucion_count");
    event.preventDefault()
};
var handle_unselect_institucion = function(event) {
    if (event.target.dataset.evref !== "handle_select_institucion")
        return;
    handle_unselect_menu(event, "preview-instituciones", "selected_institucion_menu", "institucion_count", "instituciones_menu")
};
var timeout_search_institucion = null;
var handle_input_search_institucion = function(event) {
    var instituciones_menu_element = document.getElementById("instituciones_menu");
    if (!instituciones_menu_element || !Array.isArray(instituciones))
        return;
    clearTimeout(timeout_search_institucion);
    timeout_search_institucion = setTimeout(function() {
        var _event_target_value_trim, _event_target_value;
        var pattern_value = (_event_target_value = event.target.value) === null || _event_target_value === void 0 ? void 0 : (_event_target_value_trim = _event_target_value.trim()) === null || _event_target_value_trim === void 0 ? void 0 : _event_target_value_trim.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        var pattern = new RegExp(pattern_value,"i");
        var filter = instituciones.filter(function(institucion) {
            var _institucion_nombre;
            return pattern.test((_institucion_nombre = institucion.nombre) === null || _institucion_nombre === void 0 ? void 0 : _institucion_nombre.normalize("NFD").replace(/[\u0300-\u036f]/g, ""))
        }).slice(0, 10);
        if (filter.length > 0) {
            var menu_content = "                \n                ".concat(filter.map(function(institucion) {
                return exist_item_on_selected("selected_institucion_menu", institucion.id) ? "" : '\n                    <label class="block text-slate-300 cursor-pointer hover:bg-slate-600 w-full" data-evref="handle_select_institucion" data-nombre="'.concat(institucion.nombre, '">\n                        <input type="checkbox" class="pointer-events-none" name="instituciones[]" value="').concat(institucion.id, '">\n                        <span class="pointer-events-none w-full">').concat(institucion.nombre, "</span>\n                    </label>")
            }).join(""), "\n            ");
            instituciones_menu_element.innerHTML = menu_content
        } else {
            instituciones_menu_element.innerHTML = '<li class="pb-1 text-slate-300 cursor-not-allowed">Sin resultados</li>'
        }
    }, 300)
};
var exist_item_on_selected = function() {
    var element_id = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : ""
      , payload = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : 0;
    var selected_menu_element = document.getElementById(element_id);
    if (!selected_menu_element)
        return;
    var index_item = _to_consumable_array(selected_menu_element.querySelectorAll("input")).findIndex(function(item) {
        return parseInt(item.value) === payload
    });
    return index_item >= 0
};
var handle_select_menu = function(event) {
    var preview_items = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : ""
      , item_selected = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : ""
      , count_item = arguments.length > 3 && arguments[3] !== void 0 ? arguments[3] : "";
    var preview_div_element = document.getElementById(preview_items);
    var selected_menu_element = document.getElementById(item_selected);
    var count_span_element = document.getElementById(count_item);
    if (!preview_div_element || !selected_menu_element || !count_span_element)
        return;
    var nombre = event.target.dataset.nombre;
    if (!nombre)
        return;
    var selected = selected_menu_element.querySelectorAll("label");
    if (selected.length >= 3) {
        event.preventDefault();
        return
    }
    event.target.querySelector("input").checked = true;
    selected_menu_element.appendChild(event.target);
    var selected_items = selected_menu_element.querySelectorAll("label");
    var selected_nombres = _to_consumable_array(selected_items).map(function(label) {
        return "".concat(label.dataset.nombre)
    }).join(", ");
    preview_div_element.innerHTML = selected_nombres;
    count_span_element.textContent = "(".concat(selected_items.length, "/3)")
};
var handle_unselect_menu = function(event) {
    var preview_items = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : ""
      , item_selected = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : ""
      , count_item = arguments.length > 3 && arguments[3] !== void 0 ? arguments[3] : ""
      , item_unselected = arguments.length > 4 && arguments[4] !== void 0 ? arguments[4] : "";
    var preview_div_element = document.getElementById(preview_items);
    var selected_menu_element = document.getElementById(item_selected);
    var count_span_element = document.getElementById(count_item);
    var unselected_menu_element = document.getElementById(item_unselected);
    if (!preview_div_element || !selected_menu_element || !count_span_element || !unselected_menu_element)
        return;
    var nombre = event.target.dataset.nombre;
    if (!nombre)
        return;
    unselected_menu_element.prepend(event.target);
    var selected_items = selected_menu_element.querySelectorAll("label");
    if (selected_items.length === 0) {
        preview_div_element.innerHTML = "Todos"
    } else {
        var selected_nombres = _to_consumable_array(selected_items).map(function(label) {
            return "".concat(label.dataset.nombre)
        }).join(", ");
        preview_div_element.innerHTML = selected_nombres
    }
    count_span_element.textContent = "(".concat(selected_items.length, "/3)")
};
var handle_select_departamento = function(event) {
    var departamento_menu_element = document.getElementById("departamento_menu");
    var departamentos_count_span_element = document.getElementById("departamentos_count");
    var preview_departamentos_div_element = document.getElementById("preview-departamentos");
    if (!departamento_menu_element || !departamentos_count_span_element || !preview_departamentos_div_element) {
        event.preventDefault();
        return
    }
    var departamento_filters = departamento_menu_element.querySelectorAll("input:checked");
    if (departamento_filters.length > 3) {
        event.preventDefault();
        return
    }
    departamentos_count_span_element.textContent = "(".concat(departamento_filters.length, "/3)");
    preview_departamentos_div_element.innerHTML = departamento_filters.length === 0 ? "<span>Todos</span>" : _to_consumable_array(departamento_filters).map(function(departamento) {
        return "<span>".concat(departamento.dataset.nombre, "</span>")
    }).join(", ")
};
var handle_open_filtros_mobile = function() {
    var open = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : true;
    var filtros_aside_element = document.getElementById("filtros");
    if (!filtros_aside_element)
        return;
    if (open) {
        filtros_aside_element.classList.remove("hidden");
        filtros_aside_element.classList.add("fixed");
        document.body.classList.add("overflow-hidden", "md:overflow-auto")
    } else {
        filtros_aside_element.classList.remove("fixed");
        filtros_aside_element.classList.add("hidden");
        document.body.classList.remove("overflow-hidden", "md:overflow-auto")
    }
};
var handle_validate_position_element = function(event) {
    var _event_target_dataset;
    if (((_event_target_dataset = event.target.dataset) === null || _event_target_dataset === void 0 ? void 0 : _event_target_dataset.validatePosition) !== "true") {
        return
    }
    var location = event.target.getBoundingClientRect();
    var center_screen = window.innerHeight / 2;
    var is_top = location.top + location.height / 2 < center_screen;
    if (is_top) {
        event.target.nextElementSibling.classList.add("top-full");
        event.target.nextElementSibling.classList.remove("bottom-full")
    } else {
        event.target.nextElementSibling.classList.add("bottom-full");
        event.target.nextElementSibling.classList.remove("top-full")
    }
};
var focus_filter_element = function(event) {
    var filter_aside_element = document.getElementById("filtros");
    if (!filter_aside_element)
        return;
    filter_aside_element.focus();
    event.target.classList.remove("md:flex")
};
var handle_show_button_to_up = function() {
    var button_top_element = document.getElementById("button-top");
    var limit_button_top_article_element = document.getElementById("limit_button_top");
    if (!button_top_element || !limit_button_top_article_element)
        return;
    new IntersectionObserver(function(param) {
        var _param = _sliced_to_array(param, 1)
          , entry = _param[0];
        if (entry.isIntersecting || entry.boundingClientRect.top <= 0) {
            button_top_element.classList.add("md:flex")
        } else {
            button_top_element.classList.remove("md:flex")
        }
    }
    ,{
        root: null
    }).observe(limit_button_top_article_element)
};
document.addEventListener("DOMContentLoaded", function() {
    handle_show_button_to_up()
});
