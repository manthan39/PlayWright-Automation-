const {Given,When,Then,DefineStep}=require('@cucumber/cucumber')

Given("I visit a login page", async function(){
    await page.goto('https://google.com')
})

