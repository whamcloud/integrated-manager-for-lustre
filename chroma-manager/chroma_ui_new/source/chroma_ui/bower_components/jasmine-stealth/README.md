# jasmine-stealth

[![Build Status](https://secure.travis-ci.org/searls/jasmine-stealth.png)](http://travis-ci.org/searls/jasmine-stealth)


jasmine-stealth is a [Jasmine](https://github.com/pivotal/jasmine) helper that adds a little sugar to Jasmine's spies.

**[Download the latest version here](https://github.com/searls/jasmine-stealth/releases/0.0.12/1752/jasmine-stealth.js)**.

# Conditional Stubbing

## "when" + "thenReturn"

One annoyance with Jasmine spies is the default semantics of `Spy#andReturn` limits you to a single return value, regardless of which arguments a spy is invoked with. However, the arguments a spy is called with *usually matter* to the spec. None of your out-of-the-box options are great:

1. You could instead use `Spy#andCallFake` to return conditionally. But this isn't very expressive, and may grow fatter if more conditions are added.

2. You could write an additional `it` that uses `toHaveBeenCalledWith`, but then we're verifying the same call that we're stubbing, which requires the spec to be redundant in order to be complete.

3. You could just leave the arguments unspecified and leave the spec as incomplete.

Enter jasmine-stealth, which adds a `#when` method to Jasmine's spies. It lets you specify a conditional stubbing by chaining `thenReturn`. Example:

``` javascript
describe("multiple stubbings", function() {
  var someSpy;
  beforeEach(function() {
    someSpy = jasmine.createSpy();
    someSpy.when("pirate", { booty: ["jewels",jasmine.any(String)]}).thenReturn("argh!");
    someSpy.when("panda",1).thenReturn("sad");
  });

  it("stubs the first accurately", function() {
    expect(someSpy("pirate",{ booty: ["jewels","coins"]})).toBe("argh!");
  });

  it("stubs the second too", function() {
    expect(someSpy("panda",1)).toBe("sad");
  });

  it("doesn't return anything when a stubbing isn't satisfied",function(){
    expect(someSpy("anything else at all")).not.toBeDefined();
  });
});
```

It's worth noting that Jasmine matchers will work with when-thenReturn (see the usage of `jasmine#any` above).

### "whenContext"

Sometimes you want conditional stubbing, but based on the value of `this` as opposed to the arguments passed to a method. Specifying interactions with jQuery plugins is where I seem to need this most. For that case, you can use `whenContext` in place of `when`, like so:

``` javascript
spyOn($.fn,'show');

$.fn.show.whenContext($('body')).thenReturn("a completely contrived example.")
```

### thenCallFake

You can also use `thenCallFake` (just like jasmine's `andCallFake` on vanilla spies).

``` javascript
someSpy.when("correct","params").thenCallFake(function(){ window.globalsRock = true; });

someSpy("correct","params");

expect(window.globalsRock).toBe(true);
```

# Spying on constructors

jasmine-stealth adds a facility to spy on a constructor. That way, when your subject code
that's under test instantiates a collaborator, you can access its methods as a collection of spies.

Say we have a `view` that instantiates a `model`. Here's an example spec that uses `spyOnConstructor` to isolate the view from the model.

``` coffee
#source
class window.View
  serialize: ->
    model: new Model().toJSON()
class window.Model

#specs
describe "View", ->
  describe "#serialize", ->
    Given -> @modelSpies = spyOnConstructor(window, "Model", ["toJSON"])
    Given -> @subject = new window.View()
    Given -> @modelSpies.toJSON.andReturn("some json")
    When -> @result = @subject.serialize()
    Then -> expect(@result).toEqual
      model: "some json"
```

# Custom matchers

The problem:
Jasmine currently only comes with one matcher out-of-the-box, `jasmine.any()`. You can pass a type to it (a la `jasmine.any(Number)`) in any situation where
a variable is going to be evaluated with Jasmine's internal deep-equals function, such as with `expect().toEqual()` or `expect().toHaveBeenCalledWith()`.

Here's an passing example that uses jasmine.any():

``` javascript
var panda = {
  name: "Lulu"
}

expect(panda).toEqual({
  name: jasmine.any(String)
});
```

jasmine-stealth adds a couple of my favorite custom matchers from other test double libraries: `jasmine.argThat()` and `jasmine.captor()`

## argThat matcher

What if we wanted to specify more than just the type of the argument, but we didn't want (or weren't able) to specify the argument's exact value? That's why jasmine-stealth includes a new matcher: `jasmine.argThat()`.

Say that we wanted the panda's name was shorter than 5 characters? Well, now we can:

``` javascript
expect(panda).toEqual({
  name: jasmine.argThat(function(arg){ return arg.length < 5; })
})
```

Of course, this looks a little nicer in terser CoffeeScript:

``` coffee
expect(panda).toEqual
  name: jasmine.argThat((arg) -> arg.length < 5)
```

`jasmine.argThat()` will also work in a spy's `toHaveBeenCalledWith` expectation, like so:

``` coffee
spy = jasmine.createSpy()

spy(54)

expect(spy).toHaveBeenCalledWith jasmine.argThat (arg) -> arg < 100
expect(spy).not.toHaveBeenCalledWith jasmine.argThat (arg) -> arg > 60
```

## Argument Captors

A different approach to the same problem as above is to use argument captors. It's just another style that
may read better in some specs than `jasmine.argThat()`.

Here's a contrived example of the captor API:

``` javascript

//In our spec code's setup
var captor = jasmine.captor()
var save = jasmine.createSpy()

//Meanwhile, in our production code
save({ name: "foo", phone: "123"});

//Back in our spec
expect(save).toHaveBeenCalledWith(captor.capture())
expect(captor.value.name).toBe("foo")

```

So, when you want to capture an argument value, you first create a captor with `jasmine.captor()`, then in your expectation on the call to the spy, you call the captor's `capture()` function in place of the argument you want to capture. The captured value will be available on the captor's `value` property.

Argument captors are useful in situations where your spec is especially concerned with the details of what gets passed to some method your code depends on. They're a very handy tool in the toolbox, but keep in mind that if you find yourself frequently relying on argument captors to specify your code, it may be a smell that your code is in the (bad) habit of breaking [command-query separation](http://en.wikipedia.org/wiki/Command-query_separation).

### Summarizing matchers

To summarize, you now have several ways to get at the values that your code passes to your spec's spies:

  1. You could interrogate the spy with Jasmine's built-in properties (a la `mySpy.calls[0].args[0] === "foo"`)
  2. You could use `jamine.argThat()` and write a callback function that implies some expectation
  3. You could use jasmine-stealth's `jasmine.captor()` to capture the value during your normal `toHaveBeenCalledWith` expectation and set up any number of expectations against it.


# Other goodies jasmine-stealth adds

## mostRecentCallThat

Sometimes it's helpful to look for a certain call based on some arbitrary criteria (usually the arguments it was passed with).

jasmine-stealth adds the method `mostRecentCallThat(truthTest,context)` to each spy, and it can be used to nab the call you want by passing in a truth test.

See this example:

``` javascript

spy = jasmine.createSpy();
spy('foo',function(){});
spy('bar',function(){});
spy('baz',function(){});

var barCall = spy.mostRecentCallThat(function(call) {
  return call.args[0] === 'bar';
}); //returns the invocation passing 'bar'

barCall.args[1]() //invoke the function argument on that call (presumably to test its behavior)

```

You can also pass mostRecentCallThat a context (a value for `this` if the truth test needs access to a `this` object.)

## #createStubObj

Sometimes you want a fake object that stubs multiple functions. Jasmine provides `jasmine.createSpyObj`, which takes a name and an array of function names as parameters, but it doesn't make it any easier to set up stubbings for each of those passed functions.

Here's an example:

``` javascript

var person = jasmine.createStubObj('person',{
  name: "Steve",
  salary: 1.00,
  stealAnIdea: function(){ throw "I'm going to sue you!"; }
});

```

Following the above, `person.name()` is a normal jasmine spy configured to return steve (with `andReturn`). Likewise, invoking `person.salary()` will return `1.00`. You can also pass in functions as stubs, which will be passed to `andCallFake`; therefore, invoking `person.stealAnIdea()` will throw an exception.

*Disclaimer: If you find yourself setting up many functions on a stub, beware: complex stubs are smell that there's excessive coupling between the code under test and the dependency being faked.*

## Other stub aliases

I can [often](http://searls.heroku.com/2011/06/03/whats-wrong-with-rubys-test-doubles/) [be](https://github.com/pivotal/jasmine/issues/88#issuecomment-2132975) [found](http://stackoverflow.com/questions/5208089/are-there-any-test-spy-libraries-available-for-objective-c) [complaining](https://github.com/searls/gimme) about the nomenclature of test doubles. One reason: when test double libraries conflate stubbing and verifying, developers not versed in Test Double Science™ get confused more frequently.

I love spies (over mocks) for verification. But most of the time I don't need verification; I only want to stub behavior.

So in jasmine-stealth, I've added a couple aliases to Jasmine's spy creation to allow spec authors to discriminate their intent. They are:

    jasmine.createStub("a stub for #myMethod");

And

    stubFor(myObject,"bestMethodEver");

Both will create spies, but now the spec's intent will be a tad more clear. Especially when building a heavy-weight dependency in a `beforeEach` like this one:

``` javascript
var subject,dependency;
beforeEach(function(){
  dependency = {
    query: jasmine.createStub("#query"),
    count: jasmine.createStub("#count"),
    save: jasmine.createSpy("#save")
  }
  subject = Subject(dependency);
});
```

That might help the reader figure out your intent, but obviously you're free to take it or leave it.

# Using with Node.js

To use this helper with Jasmine under Node.js, simply add it to your package.json with

``` bash
$ npm install jasmine-stealth --save-dev
```

And then from your spec (or in a spec helper), `require('jasmine-stealth')`. Be
sure that it's loaded after jasmine itself is added to the `global` object, or else
it will load `minijasminenode` which will, in turn, load jasmine
into `global` for you (which you may not be intending).
