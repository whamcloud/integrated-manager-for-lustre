Chroma UI Style Guide
---------------------

Introduction
____________
This page serves as a best practice of sorts for front-end development. Please check back often as it will
be updated frequently.

JavaScript
__________
  **spacing:** Code blocks should be indented using two spaces, Including continuation indents.

    **Example:** ::

      function foo (bars) {
        return bars.map(function (bar) {
          return bar
            .add(5)
            .divide(10);
        })
      }

    |

  **naming:** Use: ``functionNamesLikeThis, variableNamesLikeThis, ClassNamesLikeThis, EnumNamesLikeThis, methodNamesLikeThis, CONSTANT_VALUES_LIKE_THIS``.
  These are the predominant naming conventions in the JavaScript community and will make our code more familiar and consistent for new front-end developers.
  It also brings consistency when reading third-party libraries.

    |


  **use strict:** The outermost function scope of a module should have ``'use strict';`` as it's first statement.

  If it does not make sense to have a top level function, an iife(immediately invoked function expression) can be used instead.

  Strict mode should never be used globally, as it may effect other code that is not meant to run in strict mode.

    **Example (no iife):** ::

      function bazFactoryModule (bar) {
        'use strict';

        function Baz() {
          this.bar = bar;
        }

        return new Baz();
      }

    **Example (iife):** ::

      (function iife() {
        'use strict';

        function Baz() {
          this.bar = 'bar';
        }

        Baz.prototype.fooBar = function () {
          return 'foobar';
        };

        return new Baz();
      }());

  **var:** Each variable declaration should begin with ``var``. One declaration per line.

    **Example:** ::

      var foo = 'bar';
      var baz = 'bat';

    |

  **strings:** Prefer ``'`` over ``"``.
    |

  **documentation:** All files, classes, methods and properties should be documented with `JSDoc <http://usejsdoc.org/>`_ comments with the appropriate tags and types.

  Textual descriptions for methods, method parameters and method return values should be included unless obvious from the method or parameter name.

  Inline comments should be of the // variety.

  Avoid sentence fragments. Start sentences with a properly capitalized word, and end them with punctuation.
    |

  **Prefer iteration methods over loops:** For loops require unnecessary setup and boilerplate, where errors can be made.
  We target ES5, and with that there are a number of iteration methods at our disposal.

    **Don't do:** ::

      var out = [];
      for (var i = 0, n = foos.length; i < n; i++) {
        out.push(foos[i].trim());
      }

    **Do:** ::

      var out = foos.map(function (foo) {
        return foo.trim();
      });

    |


  **Prefer naming / declaring your functions:** Functions should be declared over using an expression. An exception to this rule is when functions are being created / chosen in a conditional. Declared functions are hoisted to the top of their scope, meaning they can be called before they are declared.

    **Example:** ::

      var bar = foo();

      function foo () {
        return 'bar';
      }

    Additionally, named functions provide better stacktraces when errors occur.

    **Example:** ::

      function getBaz(function gotBaz (baz) {
        return baz + 2;
      })

    |

  **Prefer storing methods on a prototype over storing them on an object literal or instance object:** If you think a class is going to be instantiated more than once, you should store it's instance methods on it's prototype.
  This way they are stored once and copies are not created when the object is.


    **Don't do (If you think your class is going to be instantiated more than once):** ::

      return {
        name: 'foo',
        getName: function getName() {
          return this.name;
        }
      }

    **Do (If you think your class is going to be instantiated more than once):** ::

      function Bar () {
        this.name = 'foo';
      }

      Bar.prototype.getName = function getName() {
        return this.name;
      }

    |

  **Prefer string formatting over concatenation**

    **Don't do:** ::

      var foo = 'foo';
      var fooBar = foo + 'bar';

    **Do:** ::

      var fooBar = '%sbar'.sprintf(foo);

    |
