const {Given,When,Then,DefineStep}=require('@cucumber/cucumber')
const { expect } = require('chai')


Given("I visit a login page", async function(){
    await page.goto('http://testyou.in')
    await page.click('#ctl00_headerTop_Signin')
})

When("Enter Username", async function(){
    await page.fill('#ctl00_indexLogin2_txtUserLogin','manthan39')
})

When("Enter password", async function(){
    await page.fill('#ctl00_indexLogin2_txtPassword','Admin@1234')
})

When ("Click on the Login Button", async function(){
    await page.locator('#ctl00_indexLogin2_lnkbtnSiginIn').click()
})

Then ("Verify the logo", async function(){
    await page.screenshot({path:'screnshot.png',fullPage:true})
    await page.locator('text=Home').waitFor();
    const title = await page.title()
    console.log(title)
    expect(title).to.equal('Student Dashboard | Test Maker - TestYou')
    
})

Then("login from the application", async function(){
    await page.click('#ctl00_headerTopStudent_lnkbtnSignout')
})
