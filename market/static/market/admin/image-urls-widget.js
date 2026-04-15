(function () {
  function createRow(inputName, value) {
    var row = document.createElement("div");
    row.className = "image-urls-widget__row";
    row.setAttribute("data-image-urls-row", "");
    row.innerHTML = [
      '<input type="url" name="' + inputName + '" value="' + (value || "") + '" class="vTextField image-urls-widget__input" placeholder="https://example.com/image.jpg">',
      '<button type="button" class="button image-urls-widget__remove" data-image-urls-remove>Remove</button>'
    ].join("");
    return row;
  }

  function syncRemoveState(widget) {
    var rows = widget.querySelectorAll("[data-image-urls-row]");
    rows.forEach(function (row) {
      var removeButton = row.querySelector("[data-image-urls-remove]");
      if (removeButton) {
        removeButton.disabled = rows.length === 1;
      }
    });
  }

  function initWidget(widget) {
    if (widget.dataset.bound === "true") {
      return;
    }
    widget.dataset.bound = "true";

    var list = widget.querySelector("[data-image-urls-list]");
    var addButton = widget.querySelector("[data-image-urls-add]");
    var firstInput = widget.querySelector("input[name]");
    var inputName = firstInput ? firstInput.name : "image_urls_items";

    addButton.addEventListener("click", function () {
      var row = createRow(inputName, "");
      list.appendChild(row);
      syncRemoveState(widget);
      var input = row.querySelector("input");
      if (input) {
        input.focus();
      }
    });

    widget.addEventListener("click", function (event) {
      var removeButton = event.target.closest("[data-image-urls-remove]");
      if (!removeButton) {
        return;
      }
      var row = removeButton.closest("[data-image-urls-row]");
      if (!row) {
        return;
      }
      if (list.querySelectorAll("[data-image-urls-row]").length === 1) {
        var input = row.querySelector("input");
        if (input) {
          input.value = "";
          input.focus();
        }
        return;
      }
      row.remove();
      syncRemoveState(widget);
    });

    syncRemoveState(widget);
  }

  function bootstrap() {
    document.querySelectorAll("[data-image-urls-widget]").forEach(initWidget);
  }

  document.addEventListener("DOMContentLoaded", bootstrap);
  document.addEventListener("formset:added", bootstrap);
})();
